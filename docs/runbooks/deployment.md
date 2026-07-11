# Deployment Runbook

## Local

```bash
docker compose up --build
make migrate
make health
```

## Production

```bash
docker compose -f docker-compose.yml -f infrastructure/compose/docker-compose.prod.yml up -d
```
