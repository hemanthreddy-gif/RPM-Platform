# ADR 001: Use a modular monolith

## Status

Accepted, 2026-11-04.

## Decision

Use one FastAPI codebase and one PostgreSQL database with explicit modules and import contracts.
The clinical-rules package remains a pure isolated Python package.

## Why

The prototype needs reliable transactional integrity and a tractable local setup more than
distributed-service complexity. Module ownership and contracts keep later extraction possible.

## Consequences

Modules must own their tables and use services/DTOs rather than importing another module's ORM
models. Only the audit module will write audit records; AI will not write clinical tables.
