# MISRA Compliance Platform

Enterprise-grade MISRA C compliance platform — Phase 0 Foundation.

## Quick Start

```bash
docker compose up --build
```

## Services

| Service | URL |
|---------|-----|
| Frontend (Vite) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Nginx Gateway | http://localhost:8080 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| Clang Worker (gRPC) | localhost:50051 |

## Health Checks

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/ready
```

## Makefile

```bash
make dev       # Start development stack with hot reload
make up        # Start detached stack
make down      # Stop stack
make build     # Build all images
make migrate   # Run Alembic migrations
make test      # Run test suites
make lint      # Run linters
make format    # Format code
make health    # Verify health endpoints
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system blueprint.
