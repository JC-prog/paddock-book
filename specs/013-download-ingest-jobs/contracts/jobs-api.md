# Contract: Background Jobs API

Base path: `/v1/admin/jobs`. Every address here requires a valid
`Authorization: Bearer <access_token>` header whose account has
`is_admin: true`, via the existing `require_admin` dependency (feature
012) — matching every other `/v1/admin/*` address.

## `POST /v1/admin/jobs/download`

Triggers a download job (FR-001).

**Request**:

```json
{ "category_id": "110" }
```

**Response** `201 Created` — the created job record (see "Job record
shape" below), `status: "queued"`.

Saves to `data/regulations/<category_id>` — not admin-configurable
(research.md).

## `POST /v1/admin/jobs/ingest`

Triggers an ingest job (FR-002).

**Request**:

```json
{ "subfolder": "110", "department": "sporting" }
```

`department` must be one of `sporting`, `technical`, `financial`
(feature 006's existing set).

**Response** `201 Created` — the created job record, `status: "queued"`.

## `GET /v1/admin/jobs`

Returns every job run, newest first — both currently active jobs
(FR-005) and history (FR-006). The frontend distinguishes "active" from
"history" by `status`, not by a separate address (research.md).

**Response** `200 OK`:

```json
[
  {
    "id": "b1f2...",
    "job_type": "download",
    "target": "110",
    "status": "running",
    "params": { "category_id": "110" },
    "result": null,
    "error": null,
    "triggered_by_email": "admin@team.example",
    "created_at": "2026-08-09T10:00:00Z",
    "started_at": "2026-08-09T10:00:01Z",
    "finished_at": null
  }
]
```

## Job record shape

Every job record (returned by all three addresses above) has this
shape:

| Field | Type | Notes |
|---|---|---|
| `id` | `string` | |
| `job_type` | `"download"` \| `"ingest"` | |
| `target` | `string` | Category identifier or subfolder name. |
| `status` | `"queued"` \| `"running"` \| `"succeeded"` \| `"failed"` | |
| `params` | `object` | The full input the admin supplied. |
| `result` | `object` \| `null` | `null` until the job reaches a final status. Shape depends on `job_type` — see data-model.md. |
| `error` | `string` \| `null` | Set only if the job failed before producing any per-item results. |
| `triggered_by_email` | `string` | |
| `created_at` | `string` (ISO 8601) | |
| `started_at` | `string` (ISO 8601) \| `null` | |
| `finished_at` | `string` (ISO 8601) \| `null` | |

## Error responses

| Status | When |
|---|---|
| `401 Unauthorized` | No valid `Authorization` header. |
| `403 Forbidden` | Valid session, but `is_admin` is `false`. |
| `422 Unprocessable Entity` | `POST` body is missing a required field, or `department` isn't one of the three known values. |
| `400 Bad Request` | An ingest job's `subfolder` would resolve outside `data/regulations/` (FR-002a). |
| `409 Conflict` | A job of the same type and target is already `queued` or `running` (FR-014). |
| `502 Bad Gateway` | The job could not be enqueued (the task queue was unreachable at trigger time — research.md). The job record is still created, marked `failed`, with `error` explaining why. |

## Non-goals

- No endpoint here retries a failed job — an admin triggers a new one
  (FR-012).
- No endpoint here streams logs or live output from a running job —
  only the coarse `status`/`result` fields above (spec.md, out of
  scope).
- No endpoint here changes `download_category()`'s or `ingest()`'s
  existing behavior (FR-011) — these addresses only trigger and report
  on them.
