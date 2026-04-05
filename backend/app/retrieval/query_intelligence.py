"""Query intelligence — detects direct section lookups via regex patterns."""

from __future__ import annotations

import re

# Map short act abbreviations to canonical act_codes.
# Keys are uppercased before lookup so mixed-case variants (CrPC, Crpc) all match.
_ACT_CODE_MAP: dict[str, str] = {
    "IPC": "ipc",
    "CRPC": "crpc",
    "CPC": "cpc",
    "BNS": "bns",
    "IEA": "iea",
    "HMA": "hma",
    "IDA": "ida",
    "MVA": "mva",
    "NIA": "nia",
}

# Build a case-insensitive alternation that matches CrPC, crpc, CRPC etc.
_ACT_ABBREVS = "|".join(_ACT_CODE_MAP.keys())

# "Section 120A IPC" / "section 376 of CrPC" / "Section 190 CrPC"
_PATTERN_SECTION_FIRST = re.compile(
    rf"[Ss]ection\s+(\d+[A-Za-z]*)\s+(?:of\s+)?({_ACT_ABBREVS})\b",
    re.IGNORECASE,
)
# "IPC 302" / "BNS Section 103" / "CrPC section 190"
_PATTERN_ACT_FIRST = re.compile(
    rf"\b({_ACT_ABBREVS})\s+(?:[Ss]ection\s+)?(\d+[A-Za-z]*)\b",
    re.IGNORECASE,
)


def parse_query(query: str) -> dict:
    """Detect direct section lookups in *query*.

    Returns a dict with keys:
        direct_lookup (bool): True when a specific section reference found.
        act_code (str | None): Canonical act code if detected.
        section_number (str | None): Section number if detected.
    """
    m = _PATTERN_SECTION_FIRST.search(query)
    if m:
        return {
            "direct_lookup": True,
            "act_code": _ACT_CODE_MAP[m.group(2).upper()],
            "section_number": m.group(1),
        }

    m = _PATTERN_ACT_FIRST.search(query)
    if m:
        return {
            "direct_lookup": True,
            "act_code": _ACT_CODE_MAP[m.group(1).upper()],
            "section_number": m.group(2),
        }

    return {"direct_lookup": False, "act_code": None, "section_number": None}
