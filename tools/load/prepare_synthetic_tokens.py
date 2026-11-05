"""Create temporary, clearly synthetic patient tokens for a disposable k6 database only."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
from sqlalchemy import create_engine, text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--jwt-secret", required=True)
    parser.add_argument("--tokens-file", type=Path, required=True)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--prefix", default="phase10-load")
    args = parser.parse_args()
    if args.count < 1:
        raise SystemExit("--count must be positive")
    now = datetime.now(UTC)
    tokens: list[str] = []
    engine = create_engine(args.database_url)
    with engine.begin() as connection:
        for index in range(args.count):
            user_id, patient_id = uuid4(), uuid4()
            connection.execute(
                text("INSERT INTO users (id, email, role) VALUES (:id, :email, 'patient')"),
                {"id": user_id, "email": f"{args.prefix}-{index}-{user_id}@example.test"},
            )
            connection.execute(
                text("INSERT INTO patients (id, user_id, display_name) VALUES (:id, :user_id, :name)"),
                {"id": patient_id, "user_id": user_id, "name": "Phase 10 Synthetic Load Patient"},
            )
            tokens.append(
                jwt.encode(
                    {"sub": str(user_id), "role": "patient", "mfa": False, "iat": now,
                     "exp": now + timedelta(minutes=15)},
                    args.jwt_secret,
                    algorithm="HS256",
                )
            )
    args.tokens_file.write_text(json.dumps(tokens), encoding="utf-8")
    print(f"Prepared {args.count} synthetic patient tokens in {args.tokens_file}")


if __name__ == "__main__":
    main()
