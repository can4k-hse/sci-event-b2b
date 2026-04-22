#!/bin/sh
set -e

ENV=${1:-dev}
DROP=0
if [ "${2:-}" = "--drop" ]; then DROP=1; fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$SCRIPT_DIR/apps/b2c-api"
COMPOSE="docker compose -f $SCRIPT_DIR/docker-compose.yml"

case "$ENV" in
  dev)
    [ -f "$API_DIR/.env.dev" ] || cp "$API_DIR/.env.dev.example" "$API_DIR/.env.dev"

    CERTS_DIR="$SCRIPT_DIR/certs"
    mkdir -p "$CERTS_DIR"
    if [ ! -f "$CERTS_DIR/cert.pem" ]; then
      echo "Генерируем TLS-сертификат..."
      mkcert -install
      mkcert -cert-file "$CERTS_DIR/cert.pem" -key-file "$CERTS_DIR/key.pem" localhost 127.0.0.1
    fi

    if [ "$DROP" = "1" ]; then
      echo "Дропаем БД и пересоздаём..."
      $COMPOSE --env-file "$API_DIR/.env.dev" down -v
    fi

    $COMPOSE --env-file "$API_DIR/.env.dev" up -d --build
    echo "Ждём запуска API..."
    until curl -sfk https://localhost/health > /dev/null; do sleep 1; done
    $COMPOSE exec api python scripts/seed.py
    echo ""
    echo "✓ Dev окружение запущено"
    echo "  API:     https://localhost"
    echo "  Swagger: https://localhost/docs"
    echo "  DB:      localhost:5432"
    echo "  Adminer: http://localhost:8090"
    echo ""
    $COMPOSE logs -f
    ;;

  test)
    [ -f "$API_DIR/.env.test" ] || cp "$API_DIR/.env.test.example" "$API_DIR/.env.test"
    $COMPOSE --env-file "$API_DIR/.env.test" --profile test up -d db-test
    echo "Ждём тестовую БД..."
    until $COMPOSE --profile test exec db-test \
      pg_isready -U scievent > /dev/null 2>&1; do sleep 1; done
    $COMPOSE --profile test run --rm \
      -e TEST_DATABASE_URL=postgresql+asyncpg://scievent:scievent@db-test:5432/scievent_test \
      --no-deps \
      api uv run pytest tests/ -v --cov=app --cov-report=term-missing
    ;;

  *)
    echo "Usage: bootstrap.sh [dev|test] [--drop]"
    exit 1
    ;;
esac
