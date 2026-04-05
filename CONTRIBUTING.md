# Contributing to LexGrid

Thank you for your interest in contributing to LexGrid! This document provides guidelines for contributing.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/lexgrid.git
cd lexgrid

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Start services
make up
```

## Development Setup

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local backend development)
- Node.js 20+ (for local UI development)

### Services

| Service | URL | Description |
|---------|-----|-------------|
| UI | http://localhost:3000 | Next.js frontend |
| Backend | http://localhost:8000 | FastAPI backend |
| Postgres | localhost:5432 | PostgreSQL + pgvector |
| Redis | localhost:6379 | Cache + Celery broker |

## Ways to Contribute

### 🐛 Bug Reports
Use GitHub Issues with:
- Clear title describing the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details

### 💡 Feature Requests
Open an issue with:
- Problem you're solving
- Proposed solution
- Alternative approaches considered

### 🔧 Code Contributions

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature`
3. **Make** your changes with clear commit messages
4. **Test** your changes
5. **Push** to your fork
6. **Submit** a Pull Request

### 📖 Documentation

- Improve existing docs in `/docs`
- Add examples
- Fix typos and clarify

## Code Standards

### Python (Backend)

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use type hints
- Run linters: `make lint`
- Run tests: `make test`

```bash
# Linting
ruff check .

# Type checking
mypy .
```

### TypeScript/JavaScript (UI)

- Use functional components
- Follow existing patterns in codebase
- Run ESLint: `npm run lint` (inside `/ui`)

### Git Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new search filter
fix: resolve section lookup 404
docs: update API reference
refactor: simplify caching logic
test: add coverage for query endpoint
```

## Project Structure

```
lexgrid/
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/     # Route handlers
│   │   ├── models/  # Data models
│   │   ├── cache/   # Redis caching
│   │   ├── workers/ # Celery tasks
│   │   └── ...
│   └── pyproject.toml
├── ui/               # Next.js frontend
│   ├── src/
│   │   ├── app/     # Pages
│   │   ├── components/  # React components
│   │   └── lib/     # Utilities
│   └── package.json
├── infra/            # Docker Compose
│   ├── docker-compose.yml
│   └── postgres/
├── docs/            # Documentation
├── legal-acts/      # Source data (gitignored)
└── Makefile         # Development commands
```

## Getting Help

- Open a [GitHub Discussion](https://github.com/your-org/lexgrid/discussions)
- Check existing [Issues](https://github.com/your-org/lexgrid/issues)
- Review [Documentation](docs/)

## Code of Conduct

Be respectful and inclusive. See our [Code of Conduct](CODE_OF_CONDUCT.md) for details.

---

Made with ❤️ for open legal tech