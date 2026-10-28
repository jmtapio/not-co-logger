# Not-co-logger

Not-co-logger is a simple Python library to help log things to stdout in a 
specific JSON format. It is inspired by the checkout-logger TypeScript 
library (https://github.com/CheckoutFinland/checkout-logger).

## Python support

Supported Python versions are **3.11, 3.12, 3.13, 3.14, and 3.15**.
CI runs the test suite on each of these versions. We target Python releases
receiving upstream bug fixes or security updates; see the
[Python version status](https://devguide.python.org/versions/).
New Python releases are added to this list after CI validation.

The next release requires Python 3.11 or newer, dropping support for Python 3.9
and 3.10. Applications using those versions must upgrade Python before upgrading
from notcologger 0.2.1.

## How to use

This guide is short and in need of much verbosity.

The idea behind this library is that typically in a complex cloud environment it makes ones life much easier if apps log to stdout in a consistent JSON format. This library implements in a pretty simple form some practices that have been found useful.

LogSpan(requestId) creates a logspan object, which has error, warn, info and debug methods to log varying levels of messages. All messages have a type (for example "lambda.handler.start"), message, log group (for example technical or session), and optionally user (could be IP or user id) and meta (free form object).

A good logtype is unique or at least easily greppable. We suggest naming them hierarchically, for example 'component.module.subtask' or something like that. A logtype should be informative but not overly rigid or verbose. Message is the typical human readable part of an event. Meta should be understood as a grab bag object for any additional fields that would be considered useful for the particular log event. For example a HTTP request log event could have the requested path included in the meta object.

All log rows are bound together by the requestId when logging them. Timestamps are automatically added.

## Request context

Use `log_context()` to correlate module-level logging calls without passing a
`LogSpan` through every helper:

```python
from notcologger import info, log_context

async def handle_request(request_id):
    with log_context(requestId=request_id, meta={"service": "billing"}):
        info("request.start", "Handling request", "request")
        await process_payment()
```

All module-level `debug`, `info`, `warn`, and `error` calls in the scope use its
request ID and metadata. Use ordinary `with`, including inside async functions.
The context manager does not return a logger.

- An outer scope without `requestId` generates one ID for the entire scope.
- A nested scope inherits its parent's ID unless given a new one. Explicit IDs
  must be non-empty strings.
- Metadata merges shallowly: inner context values override parent values, and
  event-specific `meta` overrides context values. Nested objects are replaced,
  rather than recursively merged.
- Context metadata must be a JSON-serializable dictionary. It is validated and
  snapshotted when entering the scope, including nested lists and dictionaries.
  Standard JSON conversion applies (for example, tuples become arrays and numeric
  dictionary keys become strings). Bytes and exceptions are supported in event
  metadata as described below, but must be converted before binding context metadata.
- Exiting restores the previous context, including on exceptions and cancellation.
  Invalid context metadata fails before changing the active context.

Outside a context, module-level logging retains its original behavior: every call
gets a fresh request ID. Explicit `LogSpan` and `ExceptionSpan` objects remain
independent of ambient context. To correlate an explicit span, pass the request ID
and metadata to it directly. Entering an `ExceptionSpan` does not bind module-level
logging calls.

Asyncio tasks inherit the context active when they are created. Changes in a child
scope do not affect the parent or sibling tasks. A background task can retain its
inherited request context after the parent's scope exits; give unrelated background
work a new context explicitly. `asyncio.to_thread()` propagates context. For
`run_in_executor()` or thread pools, propagate deliberately with a fresh
`contextvars.copy_context().run` per submission; do not rely on implicit thread
inheritance. Context is not automatically propagated across processes or services.

## Levels

These are suggested guidelines for log levels:

* Error: The system has run into a fatal exception that requires attention from admins.
* Warning: Something went wrong, but admins do not need to be urgently alerted.
* Info: Normal logging.
* Debug: General developer friendly spam that is wanted in the logs for common "what the hell just happened" type of solving.

## Suggested group

Here are some groups that have been found to be useful:

* request: Incoming requests
* response: Outgoing responses
* session: Events related to an active session
* technical: Events related to some technical state or issues

## ExceptionSpan

When you need to log an error but only when an exception is raised, you can use ExceptionSpan context manager:

```
    with ExceptionSpan('mylog.problem', 'Doing something fails', 'technical') as log:
        do_something_that_fails()
        log.info('mylog.success', 'It worked!', 'technical')
```

If `do_something_that_fails()` fails and raises an exception, the ExceptionSpan logs an error. If the call succeeds, the optional log.info() is called. Note that ExceptionSpan does not catch the exception.



## Metadata and logging failures

`LogSpan.annotate(**values)` adds metadata to subsequent events. Event-specific
`meta` values override annotations with the same key. Logging does not modify the
supplied metadata dictionary. Bytes and exceptions directly in `meta` are converted
to strings; nested values must already be JSON serializable. Empty metadata is omitted.

`NOTCO_LOGLEVEL` accepts `debug`, `info`, `warning`, or `error`, and defaults to
`debug` for missing or unrecognized values.

Ordinary logging calls propagate serialization and output errors. When an exception
is already leaving an `ExceptionSpan` block, logging errors derived from `Exception`
are suppressed so the original exception continues to propagate.

## Running tests

```sh
python3 -m unittest discover -s tests -v
```

## Development and package validation

Create a virtual environment and install the shared development tools (requires
pip 25.1 or newer for dependency groups):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --group dev
python -m flake8
python scripts/check_package.py
```

The package check builds the source distribution and a wheel from it, validates
both with Twine, checks metadata and required files, and runs the tests against
the wheel in a clean virtual environment outside the checkout. CI runs the same
commands for every supported Python version.

To retain release artifacts locally, run `python -m build`; files are written to
`dist/`. The Poetry CLI is not required.
