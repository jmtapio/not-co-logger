# Changelog

## Unreleased

### Breaking changes

- Python 3.11 or newer is required. Support for Python 3.9 and 3.10 has been
  dropped.
- `NaN` and infinite floats in event metadata, annotations or context metadata
  now raise `ValueError`. Previously they were written as `NaN` and `Infinity`,
  which are not valid JSON. Convert these values before logging them.

### Added

- `log_context()` binds module-level logging calls to a request ID and
  metadata, including across asyncio tasks.

### Fixed

- Metadata added with `LogSpan.annotate()` is now included in logged events.
  Previously it was dropped.
- An unrecognized `NOTCO_LOGLEVEL` value now falls back to `debug`. Previously
  only `debug` events were logged in that case.
- Logging no longer modifies the `meta` dictionary passed by the caller.
- If logging fails while `ExceptionSpan` is reporting an exception, the
  original exception now propagates instead of the logging error.

## 0.2.1

- Fixed UTF-8 text being mangled in output.

## 0.2.0

- Added `ExceptionSpan`.

## 0.1.2

- Exceptions in `meta` are converted to strings.

## 0.1.1

- Bytes in log entries are converted to strings.
