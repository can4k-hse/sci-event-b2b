# SciEvent B2C API

REST API сервиса SciEvent: аутентификация по телефону (OTP + JWT), профиль пользователя,
программа мероприятия (слоты, доклады) и уведомления.

## Стек

- **Python 3.12** + **FastAPI** / **Uvicorn**
- **PostgreSQL 16**, **SQLAlchemy** (async) + **Alembic** (миграции)
- **Docker Compose**, **nginx** (TLS), **Adminer**
- Менеджер зависимостей — **uv**

## Требования

- [Docker](https://docs.docker.com/get-docker/) и Docker Compose v2
- [mkcert](https://github.com/FiloSottile/mkcert) — локальный TLS-сертификат для dev
- `curl` (для healthcheck в bootstrap-скрипте)

## Быстрый старт (dev)

```bash
./bootstrap.sh dev
```

Скрипт сам:

1. создаёт `apps/b2c-api/.env.dev` из `.env.dev.example` (если его ещё нет);
2. генерирует TLS-сертификат через `mkcert` в `certs/`;
3. собирает и поднимает контейнеры (`db`, `api`, `nginx`, `adminer`);
4. применяет миграции Alembic (`alembic upgrade head` в entrypoint контейнера `api`);
5. наполняет БД тестовыми данными (`scripts/seed.py`);
6. показывает логи.

После запуска:

| Сервис      | Адрес                      |
|-------------|----------------------------|
| API         | https://localhost          |
| Swagger UI  | https://localhost/docs     |
| PostgreSQL  | localhost:5432             |
| Adminer     | http://localhost:8090      |

### Пересоздать БД с нуля

```bash
./bootstrap.sh dev --drop
```

Флаг `--drop` останавливает контейнеры и удаляет тома (`docker compose down -v`) перед повторным запуском.

## Тесты

```bash
./bootstrap.sh test
```

Поднимает отдельную тестовую БД (`db-test`, профиль `test`) и прогоняет `pytest` с покрытием.

## Конфигурация

Переменные окружения берутся из `apps/b2c-api/.env.dev` (dev) и `apps/b2c-api/.env.test` (тесты).
Шаблоны лежат рядом — `.env.dev.example` и `.env.test.example`. Ключевые параметры:

- `DATABASE_URL` — строка подключения к PostgreSQL;
- `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` — параметры токенов;
- `OTP_*` — время жизни и rate-limit одноразовых кодов;
- `CORS_ORIGINS` — список разрешённых origin'ов.

> ⚠️ Файлы `.env.*` (без суффикса `.example`) в репозиторий не коммитятся.

## Запуск без bootstrap-скрипта

```bash
cp apps/b2c-api/.env.dev.example apps/b2c-api/.env.dev
docker compose up -d --build
# миграции применяются автоматически в entrypoint контейнера api
```

## Миграции

```bash
# создать новую ревизию
docker compose exec api alembic revision --autogenerate -m "описание"

# применить
docker compose exec api alembic upgrade head
```

## Структура

```
.
├── bootstrap.sh            # запуск dev/test окружения
├── docker-compose.yml      # db, api, nginx, adminer, db-test
├── nginx/dev.conf          # TLS-прокси на api
└── apps/b2c-api/
    ├── app/
    │   ├── main.py         # точка входа FastAPI
    │   ├── routers/        # auth, users, slots, talks, notifications
    │   ├── models/         # SQLAlchemy-модели
    │   ├── schemas/        # Pydantic-схемы
    │   ├── services/       # бизнес-логика
    │   └── utils/          # jwt, security
    ├── alembic/            # миграции
    ├── scripts/seed.py     # тестовые данные
    └── tests/              # pytest
```
