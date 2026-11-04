# ADR 004: Use SeaweedFS for local S3-compatible storage

## Status

Accepted, 2026-11-04.

## Context

The build guide named MinIO for local object storage. During Phase 0, Docker Desktop reported that
the referenced `minio/minio` image was unavailable from Docker Hub. Current MinIO AIStor images
require a separate licence flow, which is unsuitable for this free, local educational setup.

## Decision

Use the free `chrislusf/seaweedfs` container in single-node S3 mode for local development. Keep
the service behind an S3-compatible boundary; no application code depends on a SeaweedFS-specific
API. The public local S3 endpoint remains port 9000.

## Consequences

Phase 0 storage is empty and no patient images are accepted yet. Before Phase 7, reassess the
chosen local object-store image, pin a verified release, and document any production storage
choice separately.
