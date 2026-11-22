"""Entrypoint for the separately authorized Studio migration job."""
from backend.persistence import PostgresRepository

if __name__ == "__main__":
    PostgresRepository().migrate()
