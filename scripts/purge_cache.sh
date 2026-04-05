#!/usr/bin/env bash
# purge_cache.sh — Purge LexGrid Redis query cache (db=0) for testing.
#
# Usage:
#   ./scripts/purge_cache.sh                  # purge query:* keys (default)
#   ./scripts/purge_cache.sh --all            # flush entire db=0 (query cache only)
#   ./scripts/purge_cache.sh --dry-run        # show what would be deleted
#   ./scripts/purge_cache.sh --host 127.0.0.1 --port 6379
#   ./scripts/purge_cache.sh --docker         # exec into lexgrid-redis container
#
# What this script does:
#   - Targets Redis db=0 (query cache) only
#   - Leaves db=1 (Celery broker) and db=2 (Celery results) untouched
#   - Deletes keys matching the pattern "query:*" (SHA256-keyed QueryResponse objects)
#   - Reports count of deleted keys and remaining keys in db=0

set -euo pipefail
IFS=$'\n\t'

# ── Defaults ──────────────────────────────────────────────────────────────────
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly SCRIPT_NAME
readonly CACHE_DB=0
readonly KEY_PATTERN="query:*"
readonly DEFAULT_HOST="127.0.0.1"
readonly DEFAULT_PORT=6379
readonly DOCKER_CONTAINER="lexgrid-redis"

REDIS_HOST="${REDIS_HOST:-$DEFAULT_HOST}"
REDIS_PORT="${REDIS_PORT:-$DEFAULT_PORT}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
DRY_RUN=false
FLUSH_ALL=false
USE_DOCKER=false

# ── Colours ───────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    RED='' GREEN='' YELLOW='' CYAN='' BOLD='' RESET=''
fi

# ── Helpers ───────────────────────────────────────────────────────────────────
log_info()    { echo -e "${GREEN}[INFO]${RESET}  $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
log_section() { echo -e "\n${BOLD}${CYAN}==> $*${RESET}"; }

usage() {
    cat <<EOF
${BOLD}Usage:${RESET}
  $SCRIPT_NAME [OPTIONS]

${BOLD}Options:${RESET}
  -h, --host HOST       Redis host (default: ${DEFAULT_HOST}, env: REDIS_HOST)
  -p, --port PORT       Redis port (default: ${DEFAULT_PORT}, env: REDIS_PORT)
  -a, --password PASS   Redis password (env: REDIS_PASSWORD)
  -d, --docker          Exec into '${DOCKER_CONTAINER}' container instead of connecting directly
  -n, --dry-run         Show keys that would be deleted without deleting them
      --all             Flush entire db=${CACHE_DB} (not just query:* keys)
      --help            Show this help message

${BOLD}Examples:${RESET}
  # Purge query cache on localhost (default)
  $SCRIPT_NAME

  # Dry-run: see what would be deleted
  $SCRIPT_NAME --dry-run

  # Purge via Docker container (when running full stack)
  $SCRIPT_NAME --docker

  # Purge on a remote host
  $SCRIPT_NAME --host 10.0.0.5 --port 6379

  # Flush entire cache db (more aggressive)
  $SCRIPT_NAME --all

${BOLD}Redis databases:${RESET}
  db=0  Query cache (${KEY_PATTERN})  ← this script targets db=0 only
  db=1  Celery broker                 ← untouched
  db=2  Celery results                ← untouched
EOF
}

# ── Argument parsing ──────────────────────────────────────────────────────────
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--host)
                REDIS_HOST="$2"
                shift 2
                ;;
            -p|--port)
                REDIS_PORT="$2"
                shift 2
                ;;
            -a|--password)
                REDIS_PASSWORD="$2"
                shift 2
                ;;
            -d|--docker)
                USE_DOCKER=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            --all)
                FLUSH_ALL=true
                shift
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage >&2
                exit 1
                ;;
        esac
    done
}

# ── Redis command wrapper ─────────────────────────────────────────────────────
# Runs a redis-cli command either locally or inside the Docker container.
redis_cmd() {
    if [[ "$USE_DOCKER" == "true" ]]; then
        docker exec "$DOCKER_CONTAINER" redis-cli "$@"
    elif [[ -n "$REDIS_PASSWORD" ]]; then
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" --no-auth-warning "$@"
    else
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" "$@"
    fi
}

# ── Dependency checks ─────────────────────────────────────────────────────────
check_deps() {
    if [[ "$USE_DOCKER" == "true" ]]; then
        if ! command -v docker &>/dev/null; then
            log_error "docker not found. Install Docker or omit --docker."
            exit 1
        fi
        if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${DOCKER_CONTAINER}$"; then
            log_error "Container '${DOCKER_CONTAINER}' is not running."
            log_error "Start it with: cd infra && docker compose up -d redis"
            exit 1
        fi
    else
        if ! command -v redis-cli &>/dev/null; then
            log_error "redis-cli not found."
            log_error "Install: brew install redis  (macOS)  |  apt install redis-tools  (Debian/Ubuntu)"
            log_error "Or use --docker to exec into the running container."
            exit 1
        fi
    fi
}

# ── Connectivity check ────────────────────────────────────────────────────────
check_connection() {
    local pong
    pong=$(redis_cmd -n "$CACHE_DB" PING 2>/dev/null) || {
        log_error "Cannot connect to Redis."
        if [[ "$USE_DOCKER" == "true" ]]; then
            log_error "Is the '${DOCKER_CONTAINER}' container healthy?"
        else
            log_error "Is Redis running at ${REDIS_HOST}:${REDIS_PORT}?"
        fi
        exit 1
    }
    if [[ "$pong" != "PONG" ]]; then
        log_error "Unexpected PING response: ${pong}"
        exit 1
    fi
}

# ── Count keys ────────────────────────────────────────────────────────────────
count_query_keys() {
    # SCAN is safe for production — does not block like KEYS
    local count=0
    local cursor=0
    while true; do
        local result
        result=$(redis_cmd -n "$CACHE_DB" SCAN "$cursor" MATCH "$KEY_PATTERN" COUNT 100)
        cursor=$(echo "$result" | head -1)
        local batch
        batch=$(echo "$result" | tail -n +2 | grep -c . || true)
        count=$((count + batch))
        [[ "$cursor" == "0" ]] && break
    done
    echo "$count"
}

# ── Dry-run: list keys ────────────────────────────────────────────────────────
list_query_keys() {
    local cursor=0
    local keys=()
    while true; do
        local result
        result=$(redis_cmd -n "$CACHE_DB" SCAN "$cursor" MATCH "$KEY_PATTERN" COUNT 100)
        cursor=$(echo "$result" | head -1)
        while IFS= read -r key; do
            [[ -n "$key" ]] && keys+=("$key")
        done < <(echo "$result" | tail -n +2)
        [[ "$cursor" == "0" ]] && break
    done
    printf '%s\n' "${keys[@]+"${keys[@]}"}"
}

# ── Delete query:* keys via SCAN + DEL ───────────────────────────────────────
# Uses SCAN to avoid blocking Redis. Deletes in batches of up to 100.
purge_query_keys() {
    local total_deleted=0
    local cursor=0

    while true; do
        # SCAN returns: cursor on line 1, keys on subsequent lines
        local result
        result=$(redis_cmd -n "$CACHE_DB" SCAN "$cursor" MATCH "$KEY_PATTERN" COUNT 100)
        cursor=$(echo "$result" | head -1)

        # Collect keys from this batch
        local batch_keys=()
        while IFS= read -r key; do
            [[ -n "$key" ]] && batch_keys+=("$key")
        done < <(echo "$result" | tail -n +2)

        if [[ ${#batch_keys[@]} -gt 0 ]]; then
            redis_cmd -n "$CACHE_DB" DEL "${batch_keys[@]}" >/dev/null
            total_deleted=$((total_deleted + ${#batch_keys[@]}))
        fi

        [[ "$cursor" == "0" ]] && break
    done

    echo "$total_deleted"
}

# ── Flush entire db=0 ─────────────────────────────────────────────────────────
flush_cache_db() {
    redis_cmd -n "$CACHE_DB" FLUSHDB ASYNC >/dev/null
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    parse_args "$@"
    check_deps
    check_connection

    # Connection info
    if [[ "$USE_DOCKER" == "true" ]]; then
        log_info "Connected via Docker container: ${BOLD}${DOCKER_CONTAINER}${RESET}"
    else
        log_info "Connected to Redis at ${BOLD}${REDIS_HOST}:${REDIS_PORT}${RESET}"
    fi
    log_info "Targeting db=${CACHE_DB} (query cache)"

    # ── Dry-run mode ──────────────────────────────────────────────────────────
    if [[ "$DRY_RUN" == "true" ]]; then
        log_section "Dry-run — keys matching '${KEY_PATTERN}' in db=${CACHE_DB}"
        local keys
        keys=$(list_query_keys)
        if [[ -z "$keys" ]]; then
            log_info "No keys found matching '${KEY_PATTERN}' — cache is already empty."
        else
            echo "$keys"
            local count
            count=$(echo "$keys" | grep -c . || true)
            echo ""
            log_warn "Would delete ${BOLD}${count}${RESET} key(s). Re-run without --dry-run to proceed."
        fi
        exit 0
    fi

    # ── Stats before ──────────────────────────────────────────────────────────
    log_section "Cache stats before purge"
    local db_size_before
    db_size_before=$(redis_cmd -n "$CACHE_DB" DBSIZE)
    local query_count_before
    query_count_before=$(count_query_keys)
    log_info "Total keys in db=${CACHE_DB}:  ${BOLD}${db_size_before}${RESET}"
    log_info "Query cache keys (${KEY_PATTERN}): ${BOLD}${query_count_before}${RESET}"

    if [[ "$query_count_before" -eq 0 ]] && [[ "$FLUSH_ALL" == "false" ]]; then
        log_info "Cache is already empty — nothing to do."
        exit 0
    fi

    # ── Purge ─────────────────────────────────────────────────────────────────
    log_section "Purging cache"

    if [[ "$FLUSH_ALL" == "true" ]]; then
        log_warn "Flushing entire db=${CACHE_DB} (FLUSHDB ASYNC)..."
        flush_cache_db
        log_info "${GREEN}Done.${RESET} All keys in db=${CACHE_DB} deleted."
    else
        log_info "Deleting keys matching '${KEY_PATTERN}' via SCAN + DEL..."
        local deleted
        deleted=$(purge_query_keys)
        log_info "${GREEN}Done.${RESET} Deleted ${BOLD}${deleted}${RESET} key(s)."
    fi

    # ── Stats after ───────────────────────────────────────────────────────────
    log_section "Cache stats after purge"
    local db_size_after
    db_size_after=$(redis_cmd -n "$CACHE_DB" DBSIZE)
    local query_count_after
    query_count_after=$(count_query_keys)
    log_info "Total keys in db=${CACHE_DB}:  ${BOLD}${db_size_after}${RESET}"
    log_info "Query cache keys (${KEY_PATTERN}): ${BOLD}${query_count_after}${RESET}"

    if [[ "$query_count_after" -eq 0 ]]; then
        log_info "${GREEN}Cache is clean.${RESET}"
    else
        log_warn "${query_count_after} key(s) remain — this is unexpected."
    fi

    # Reminder about Celery dbs
    echo ""
    log_info "Celery broker (db=1) and results (db=2) were ${BOLD}not${RESET} touched."
}

main "$@"
