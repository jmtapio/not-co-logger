import sys
import os
import datetime
import json
import uuid
from contextlib import contextmanager
from contextvars import ContextVar

__all__ = ['LogSpan', 'ExceptionSpan', 'debug', 'info', 'warn', 'error', 'log_context']


_loglevel_map = {
    'debug': ('debug', 'info', 'warning', 'error'),
    'info': ('info', 'warning', 'error'),
    'warning': ('warning', 'error'),
    'error': ('error',)
    }


# Store immutable JSON text so inherited contexts never share mutable metadata.
_log_context = ContextVar('notcologger_context', default=None)


@contextmanager
def log_context(requestId=None, meta=None):
    """Bind module-level logs to a request ID and a JSON snapshot of metadata.

    Nested scopes inherit the request ID unless one is supplied. Metadata is
    merged with the parent, with inner values taking precedence. Explicit
    LogSpan and ExceptionSpan instances remain independent of this context.
    """
    parent = _log_context.get()
    if requestId is None:
        requestId = parent[0] if parent else str(uuid.uuid4())
    if not isinstance(requestId, str) or not requestId:
        raise ValueError('requestId must be a non-empty string or None')
    metadata = json.loads(parent[1]) if parent else {}
    if meta is not None:
        if not isinstance(meta, dict):
            raise TypeError('meta must be a dictionary or None')
        metadata.update(meta)
    # Validate and snapshot before changing the active context.
    state = (requestId, json.dumps(metadata, ensure_ascii=False))
    token = _log_context.set(state)
    try:
        yield
    finally:
        _log_context.reset(token)


def _module_span():
    state = _log_context.get()
    span = LogSpan(state[0] if state else None)
    if state:
        span.annotation = json.loads(state[1])
    return span


class LogSpan:
    """Logger object for a single context, such as request

    Logger can be given a specific requestId to help group all
    loggings made with self logger, or one can be generated
    automatically.
    """
    
    def __init__(self, requestId=None):
        self.requestId = requestId or str(uuid.uuid4())
        self.annotation = dict()
        self._stdout = sys.stdout

    def _make_timestamp(self):
        return datetime.datetime.now().isoformat()

    def _output(self, loglevel='info', **kwargs):
        # Check if self loglevel should get logged, default to debug if unknown level
        if loglevel not in _loglevel_map.get(os.environ.get('NOTCO_LOGLEVEL', 'debug'), _loglevel_map['debug']):
            return

        if 'user' in kwargs and kwargs['user'] is None:
            kwargs['user'] = 'SYSTEM'

        meta = dict()
        meta.update(self.annotation)
        meta.update(kwargs.get('meta', None) or dict())

        logentry = dict(timestamp=self._make_timestamp(), level=loglevel, rid=self.requestId)
        logentry.update(kwargs)

        if meta:
            logentry['meta'] = meta
        else:
            logentry.pop('meta', None)

        for key in logentry:
            if isinstance(logentry[key], bytes):
                logentry[key] = logentry[key].decode('utf-8', errors='ignore')

        if isinstance(logentry.get('meta'), dict):
            meta = logentry['meta']
            for key in meta:
                if isinstance(meta[key], bytes):
                    meta[key] = meta[key].decode('utf-8', errors='ignore')
                elif isinstance(meta[key], BaseException):
                    meta[key] = repr(meta[key])

        self._stdout.write('{}\n'.format(json.dumps(logentry, ensure_ascii=False, skipkeys=True)))

        if loglevel != 'debug':
            self._stdout.flush()

    def annotate(self, **kwargs):
        """Add key-value-pairs to add to new logged entrie's metadata

        Self method can be used to add recurring metadata items such
        as session id's.
        """

        # Test if the annotated values are JSON serializable, throw an exception if not
        json.dumps(kwargs)

        self.annotation.update(kwargs)

    def debug(self, logtype, message, group=None, user=None, meta=None):
        """Log a debug entry

        logtype: a string identifying this logging location, for example "lambda.handler.start"
        message: human readable message
        group: log group, for example technical, session or request
        user: some kind of user identifier
        meta: dictionary of free form data
        """
        self._output(
            loglevel='debug',
            type=logtype,
            message=message,
            group=group,
            user=user,
            meta=meta)

    def info(self, logtype, message, group, user=None, meta=None):
        """Log an info message

        logtype: a string identifying this logging location, for example "lambda.handler.start"
        message: human readable message
        group: log group, for example technical, session or request
        user: some kind of user identifier
        meta: dictionary of free form data
        """
        self._output(
            loglevel='info',
            type=logtype,
            message=message,
            group=group,
            user=user,
            meta=meta)

    def warn(self, logtype, message, group, user=None, meta=None):
        """Log a warning

        logtype: a string identifying this logging location, for example "lambda.handler.start"
        message: human readable message
        group: log group, for example technical, session or request
        user: some kind of user identifier
        meta: dictionary of free form data
        """
        self._output(
            loglevel='warning',
            type=logtype,
            message=message,
            group=group,
            user=user,
            meta=meta)

    def error(self, logtype, message, group, user=None, meta=None):
        """Log an error

        logtype: a string identifying this logging location, for example "lambda.handler.start"
        message: human readable message
        group: log group, for example technical, session or request
        user: some kind of user identifier
        meta: dictionary of free form data
        """
        self._output(
            loglevel='error',
            type=logtype,
            message=message,
            group=group,
            user=user,
            meta=meta)


class ExceptionSpan(LogSpan):
    """Logger that is activated when an exception is raised in a with-block

    Usage example:

    with ExceptionSpan('mylog.problem', 'Doing something fails', 'technical') as log:
        do_something_that_fails()

    """

    def __init__(self, logtype, message, group, requestId=None, level='error', user=None, meta=None):
        super().__init__(requestId)
        self.default_level = level
        self.default_logtype = logtype
        self.default_message = message
        self.default_group = group
        self.default_user = user
        self.annotation = dict(meta or {})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            try:
                self._output(
                    loglevel = self.default_level,
                    type     = self.default_logtype,
                    message  = self.default_message,
                    group    = self.default_group,
                    user     = self.default_user,
                    meta     = dict(
                        exc_type = exc_type.__qualname__,
                        exc_val = str(getattr(exc_val, 'args', ''))
                        ))
            except Exception:
                # Logging failures must not replace the exception from the block.
                pass

        # We will not catch the exception
        return None


def debug(logtype, message, group=None, user=None, meta=None):
    """Log a debug entry

    logtype: a string identifying this logging location, for example "lambda.handler.start"
    message: human readable message
    group: log group, for example technical, session or request
    user: some kind of user identifier
    meta: dictionary of free form data
    """
    span = _module_span()
    span.debug(logtype, message, group, user, meta)

def info(logtype, message, group, user=None, meta=None):
    """Log an info message

    logtype: a string identifying this logging location, for example "lambda.handler.start"
    message: human readable message
    group: log group, for example technical, session or request
    user: some kind of user identifier
    meta: dictionary of free form data
    """
    span = _module_span()
    span.info(logtype, message, group, user, meta)

def warn(logtype, message, group, user=None, meta=None):
    """Log a warning

    logtype: a string identifying this logging location, for example "lambda.handler.start"
    message: human readable message
    group: log group, for example technical, session or request
    user: some kind of user identifier
    meta: dictionary of free form data
    """
    span = _module_span()
    span.warn(logtype, message, group, user, meta)

def error(logtype, message, group, user=None, meta=None):
    """Log an error

    logtype: a string identifying this logging location, for example "lambda.handler.start"
    message: human readable message
    group: log group, for example technical, session or request
    user: some kind of user identifier
    meta: dictionary of free form data
    """
    span = _module_span()
    span.error(logtype, message, group, user, meta)
