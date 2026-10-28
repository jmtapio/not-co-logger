# Not-co-logger

Not-co-logger writes application logs to stdout as one JSON object per line,
in a fixed format. It is meant for services running in cloud environments, where
a log collector reads stdout and logs from many services end up in one place.
Consistent fields make these logs easy to search, filter and correlate.

The library is deliberately small and opinionated:

- **One JSON line per event**, written to stdout. No handlers, formatters or
  log files to configure.
- **A fixed set of fields.** Every event has a type, a human-readable message
  and a group. Anything else goes in a free-form `meta` object.
- **A request ID on every line**, so all events from one request or job can be
  found together.
- **One setting**: the minimum log level, read from an environment variable.

## Install

```sh
pip install notcologger
```

Requires Python 3.11 or newer.

## Quick start

```python
from notcologger import info

info("orders.checkout.start", "Checkout started", "request",
     user="u-42", meta={"path": "/checkout"})
```

```json
{"timestamp": "2026-10-28T09:59:36.891114", "level": "info", "rid": "e5c4be97-7ae7-4da4-a114-d0128d0c5616", "type": "orders.checkout.start", "message": "Checkout started", "group": "request", "user": "u-42", "meta": {"path": "/checkout"}}
```

The module-level functions are `debug`, `info`, `warn` and `error`. They all take
`(logtype, message, group, user=None, meta=None)`. Outside a
[request context](#request-context), each call gets a new request ID.

## Log format

| Field       | Description |
|-------------|-------------|
| `timestamp` | Local time in ISO 8601 format, added automatically. |
| `level`     | `debug`, `info`, `warning` or `error`. |
| `rid`       | Request ID that ties related events together. Generated (UUID4) if not given. |
| `type`      | What happened, as a stable identifier, e.g. `orders.checkout.start`. |
| `message`   | Human-readable description. |
| `group`     | Broad category of the event, see [Groups](#groups). |
| `user`      | User identifier, such as a user ID or IP address. Defaults to `SYSTEM`. |
| `meta`      | Free-form object with any extra data. Omitted when empty. |

## Conventions

### Log types

A log type should be unique, or at least easy to grep for. Name types
hierarchically, such as `component.module.subtask`, and make them informative
but short.

### Levels

- **error**: something failed and needs attention from administrators.
- **warning**: something went wrong, but nobody needs to be alerted urgently.
- **info**: normal operation.
- **debug**: detailed developer output that helps answer "what just happened?".

### Groups

- **request**: incoming requests
- **response**: outgoing responses
- **session**: events related to an active session
- **technical**: technical state or problems

## Usage

### LogSpan

A `LogSpan` logs events under one request ID. It has the same `debug`, `info`,
`warn` and `error` methods as the module. `annotate()` adds metadata to every
event the span logs after it; `meta` given to an individual event takes
precedence.

```python
from notcologger import LogSpan

log = LogSpan(request_id)
log.annotate(session="s-1234")
log.info("auth.login.success", "User logged in", "session", user="u-42")
```

### Request context

`log_context()` binds module-level logging calls to a request ID and metadata,
so you don't have to pass a `LogSpan` through every function:

```python
from notcologger import info, log_context

async def handle_request(request_id):
    with log_context(requestId=request_id, meta={"service": "billing"}):
        info("request.start", "Handling request", "request")
        await process_payment()  # its module-level log calls use the same rid
```

- If no `requestId` is given, a new ID is generated. In a nested context, the
  ID is inherited from the enclosing context.
- Metadata is merged one level deep: values from inner contexts override outer
  ones, and an event's own `meta` overrides both.
- Context metadata must be JSON-serializable. A snapshot is taken on entry, so
  later changes to the dictionary have no effect.
- Asyncio tasks and `asyncio.to_thread()` inherit the active context. Threads
  started in other ways do not; use `contextvars.copy_context().run` to pass it.
- `LogSpan` and `ExceptionSpan` objects ignore the context. Pass the request ID
  to them directly if you need it.

### ExceptionSpan

`ExceptionSpan` logs an error only if an exception leaves the `with` block. The
exception is not caught: it still propagates.

```python
from notcologger import ExceptionSpan

with ExceptionSpan("orders.payment.failed", "Payment failed", "technical") as log:
    charge_card()
    log.info("orders.payment.success", "Payment succeeded", "technical")
```

The error event includes the exception type and arguments in `meta`.
`ExceptionSpan` also accepts `requestId`, `level`, `user` and `meta`.

## Configuration

Set `NOTCO_LOGLEVEL` to `debug`, `info`, `warning` or `error` to choose the
minimum level that is logged. If the variable is missing or has another value,
the level is `debug`.

## Metadata and errors

- Bytes and exceptions at the top level of an event's `meta` are converted to
  strings. Everything else must be JSON-serializable.
- `NaN` and infinite floats raise `ValueError`, because they are not valid JSON.
- Logging does not modify the dictionaries you pass in.
- If an event can't be serialized or written, the logging call raises an
  exception. The exception is when `ExceptionSpan` is already logging an error
  for an exception leaving its block: then logging errors are suppressed so the
  original exception propagates unchanged.

See [CHANGELOG.md](CHANGELOG.md) for release notes.
