# CoffeeTech Transactions Service

This service handles transactions and financial reports management for the CoffeeTech platform.

## Prerequisites

- Python 3.13+
- PostgreSQL
- [uv](https://github.com/astral-sh/uv) package manager
- FastAPI
- SQLAlchemy

## Database Setup

The service connects to a PostgreSQL database using environment variables defined in the `.env` file:

```env
PGHOST=your-host
PGPORT=your-port
PGDATABASE=your_database_name
PGUSER=postgresql-database-user
PGPASSWORD=your_password
```

Configure these environment variables according to your database setup before running the service.

## Installing Dependencies

To install dependencies, run:

```bash
uv sync
```

## Running the Service (Development)

To run the service in development mode:

```bash
uv run fastapi dev --port 8004
```

## Running the Service (Production)

For production environments, use:

```bash
uv run fastapi run
```

## Docker Deployment

To build and run the service with Docker Compose:

```bash
docker compose up --build -d
```

This will build the image and start the service in detached mode, exposing it at [http://localhost:8004](http://localhost:8004).

To stop the service, run:

```bash
docker compose down
```

## Project Structure

```bash
transactions_service/
├── main.py
├── dataBase.py
├── endpoints/
├── utils/
├── pyproject.toml
├── .env
├── Dockerfile
├── docker-compose.yml
└── ...
```

## Notes

- The Dockerfile uses `uv` for dependency management and runs FastAPI directly.
- The `.dockerignore` file is used to exclude unnecessary files from the Docker build context.
- Docker Compose is now the recommended way to build and run the service in development and production.
