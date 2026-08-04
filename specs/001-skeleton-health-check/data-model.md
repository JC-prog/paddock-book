# Phase 1 Data Model: Foundational Application Skeleton with Health Check

Per the spec's Key Entities section, this feature introduces **no domain data
entities** — it establishes connectivity only, with no persistent data.

The only data shape involved is the health check's response payload, a transient DTO
(not a stored entity) returned by the backend and consumed by the frontend:

## HealthStatus (response DTO, not persisted)

| Field | Type | Description | Source requirement |
|---|---|---|---|
| `status` | string, literal `"ok"` | Indicates the backend process is running and responsive | FR-001 |

No relationships, no state transitions, no validation rules beyond the literal value —
this DTO exists purely to answer "is the backend up," per the spec's explicit exclusion
of dependency checks. The frontend derives its three UI states (healthy / unreachable /
checking, FR-004) from whether this response was received at all, not from richer
payload content:

- **Healthy**: HTTP response received with `status: "ok"`
- **Unreachable**: request failed (network error, timeout, non-2xx response)
- **Checking**: request in flight, no response yet

The full response contract is defined in [`contracts/health-api.yaml`](./contracts/health-api.yaml).
