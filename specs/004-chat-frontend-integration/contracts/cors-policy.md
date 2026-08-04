# Contract: Backend CORS Policy (updated)

This feature does not change the `/v1/chat` request/response contract —
see `specs/003-chat-api-sse/contracts/chat-api.md`, which still applies
unchanged. The only contract this feature modifies is which cross-origin
requests the backend accepts.

## Before this feature

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

`POST http://localhost:8000/v1/chat` from the frontend origin
(`http://localhost:4200`) is rejected by the browser's CORS preflight —
`GET` is the only allowed method.

## After this feature

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

**Contract guarantee**: requests to `/v1/chat` and `/health` from
`http://localhost:4200` succeed for the methods each address actually uses
(`GET` for `/health`, `POST` for `/v1/chat`). No other origin is permitted.
Any future address requiring a different method MUST extend this list
explicitly rather than widening it to `["*"]`.
