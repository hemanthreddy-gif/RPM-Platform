# ADR 002: Start with PostgreSQL before TimescaleDB

## Status

Accepted, 2026-11-04.

## Decision

Use PostgreSQL 16 with ordinary time-series indexes first. Do not add TimescaleDB unless profiling
shows a measured need.

## Why

PostgreSQL supports the transaction, row-level-security, JSON, and query needs of the initial
prototype without another operational dependency.
