# Online Banking System Backend

FastAPI backend scaffold for a mobile banking app with PostgreSQL, SQLAlchemy, Redis, JWT authentication, refresh-token rotation, RBAC, Alembic migrations, Docker support, OTP flows, transaction-safe transfers, audit logs, and admin APIs.

## Stack

- FastAPI
- PostgreSQL + SQLAlchemy 2.x async ORM
- Pydantic v2
- Alembic
- Redis
- JWT access and refresh tokens
- Passlib hashing
- Optional Celery worker

## Project Structure

```text
app/
  api/
    dependencies/
    routes/
  core/
  db/
  models/
  repositories/
  schemas/
  services/
  utils/
  workers/
alembic/
  versions/
Dockerfile
docker-compose.yml
.env.example
```

## Main Features

- Registration, login, refresh, logout, forgot password, reset password
- Email OTP verification and step-up OTP for sensitive actions
- Account lock after repeated failed logins
- Role-based access control for customer, admin, support, compliance
- User profile management and account deactivation
- Multiple bank accounts with account-number and IBAN placeholders
- Atomic internal transfers with idempotency keys and daily limit checks
- Card freeze/unfreeze and spending limit updates
- In-app notification API and communication abstraction
- Support ticket APIs
- Admin endpoints for users, transactions, account freeze/unfreeze, audit logs
- Centralized exception handling and request/security middleware

## Run Locally

1. Copy `.env.example` to `.env`.
2. Adjust secrets and connection strings.
3. Create the database and Redis instance, or use Docker Compose.
4. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

5. Run migrations:

```bash
python -m app.prestart
```

6. Start the API:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`, with docs at `/docs`.

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

This starts:

- `api` on port `8000`
- `postgres` on port `5432`
- `redis` on port `6379`
- optional `worker` when you run `docker compose --profile worker up`

The API container now waits for PostgreSQL to become reachable before applying Alembic migrations, which makes startup more reliable when Docker networking or service discovery is still warming up.

## Real Gmail SMTP

If you want OTP codes to be sent to a real Gmail inbox, configure Gmail SMTP in `.env`.

Use these values:

```env
MAIL_ENABLED=true
MAIL_HOST=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=yourbankproject@gmail.com
MAIL_PASSWORD=your-google-app-password
MAIL_USE_TLS=false
MAIL_USE_STARTTLS=true
MAIL_FROM=yourbankproject@gmail.com
MAIL_FROM_NAME=Example Bank
```

Important notes:

- Your Gmail account should have 2-Step Verification enabled.
- You should use a Google App Password, not your normal Gmail password.
- `MAIL_FROM` should usually match `MAIL_USERNAME`.
- When running in Docker, the API container will connect directly to Gmail SMTP over the internet.

## Authentication Flow

1. `POST /auth/register`
2. `POST /auth/verify-email`
3. `POST /auth/login`
4. Use the returned access token for protected endpoints.
5. Rotate refresh tokens with `POST /auth/refresh`.
6. Revoke the provided refresh token with `POST /auth/logout`.

Sensitive operations such as password change, account deactivation, and large transfers use OTP endpoints:

- `POST /auth/otp/request`
- `POST /auth/otp/verify`

## Database and Security Notes

- Passwords are stored with Passlib using a secure password-hashing scheme.
- Refresh tokens are hashed before persistence.
- Audit records are created for security-sensitive operations.
- Transfer logic uses row-level locking and a transaction boundary.
- Redis is used for OTP storage, temporary tokens, and rate limiting.
- Security headers and CORS middleware are enabled in the application factory.

## Admin Bootstrap

If `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` are set in `.env`, the app bootstraps default roles and a first admin user on startup after migrations are applied.

## Example Endpoints

- `/auth/register`
- `/auth/login`
- `/auth/refresh`
- `/auth/logout`
- `/auth/forgot-password`
- `/users/me`
- `/users/update`
- `/accounts/`
- `/accounts/{id}`
- `/transactions/transfer`
- `/transactions/history`
- `/transactions/{id}`
- `/cards/`
- `/cards/{id}/freeze`
- `/notifications/`
- `/support/`
- `/admin/login`
- `/admin/users`
- `/admin/transactions`
- `/admin/accounts/{id}/freeze`
- `/admin/audit-logs`

## Next Production Steps

- Replace mock email/SMS adapters with real providers.
- Add device binding and biometric challenge endpoints if the mobile app requires them.
- Add stronger fraud models, sanctions screening, and beneficiary management.
- Add automated tests and CI checks.
- Split async background tasks and webhooks into dedicated worker/event services as the system grows.
