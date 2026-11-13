"""One-off preview migration using an owner connection, never the web runtime login.

Run only on the private Railway worker before its long-running worker deployment.
Remove MIGRATION_DATABASE_URL from that service after successful completion.
No destructive reset or downgrade is provided.
"""

import os
import subprocess
from pathlib import Path

import psycopg
from psycopg import sql


def migrate() -> None:
    if os.environ.get("HOSTED_DEMO", "").lower() != "true":
        raise RuntimeError("This command requires the isolated hosted synthetic demo")
    owner_url = os.environ["MIGRATION_DATABASE_URL"]
    app_password = os.environ["APP_DATABASE_PASSWORD"]
    if len(app_password) < 32:
        raise RuntimeError("A generated runtime database password is required")
    connection_url = owner_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(connection_url) as connection:
        if connection.execute("SELECT current_database()").fetchone() != ("rpm_synthetic_demo",):
            raise RuntimeError("Refusing migration outside rpm_synthetic_demo")
    environment = dict(os.environ)
    environment["DATABASE_URL"] = owner_url.replace("postgresql://", "postgresql+psycopg://", 1)
    subprocess.run(
        ["alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=Path(__file__).resolve().parent.parent,
        env=environment,
        check=True,
    )
    with psycopg.connect(connection_url) as connection:
        connection.execute("""DO $$ BEGIN CREATE ROLE rpm_app LOGIN;
            EXCEPTION WHEN duplicate_object THEN NULL; END $$""")
        connection.execute(
            sql.SQL(
                "ALTER ROLE rpm_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOREPLICATION NOBYPASSRLS INHERIT PASSWORD {}"
            ).format(sql.Literal(app_password))
        )
        connection.execute("GRANT rpm_runtime TO rpm_app")
        connection.execute("GRANT CONNECT ON DATABASE rpm_synthetic_demo TO rpm_app")
        connection.execute("GRANT USAGE ON SCHEMA public TO rpm_app")
        connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC, rpm_app, rpm_runtime")
    print("Synthetic schema upgraded; restricted runtime role configured. No credentials logged.")


if __name__ == "__main__":
    migrate()
