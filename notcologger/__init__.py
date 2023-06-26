import sys
import os
import datetime
import json
import uuid

__all__ = ['LogSpan', 'ExceptionSpan', 'debug', 'info', 'warn', 'error']


_loglevel_map = {
    'debug': ('debug', 'info', 'warning', 'error'),
    'info': ('info', 'warning', 'error'),
    'warning': ('warning', 'error'),
    'error': ('error',)
    }


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
        if loglevel not in _loglevel_map.get(os.environ.get('NOTCO_LOGLEVEL', 'debug'), 'debug'):
            return

        if 'user' in kwargs and kwargs['user'] is None:
            kwargs['user'] = 'SYSTEM'

        meta = dict()
        meta.update(self.annotation)
        meta.update(kwargs.get('meta', None) or dict())

        logentry = dict(timestamp=self._make_timestamp(), level=loglevel, rid=self.requestId)
        logentry.update(kwargs)

        if not logentry['meta']: del logentry['meta']

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

        self._stdout.write('{}\n'.format(json.dumps(logentry, skipkeys=True)))

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

    with ExceptionSpan('mylog.problem', 'Doing something fails') as log:
        do_something_that_fails()

    """

    def __init__(self, logtype, message, group, requestId=None, level='error', user=None, meta=None):
        super().__init__(requestId)
        self.default_level = level
        self.default_logtype = logtype
        self.default_message = message
        self.default_group = group
        self.default_user = user
        self.annotation = meta or dict()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
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
    span = LogSpan()
    span.debug(logtype, message, group, user, meta)

def info(logtype, message, group, user=None, meta=None):
    """Log an info message

    logtype: a string identifying this logging location, for example "lambda.handler.start"
    message: human readable message
    group: log group, for example technical, session or request
    user: some kind of user identifier
    meta: dictionary of free form data
    """
    span = LogSpan()
    span.info(logtype, message, group, user, meta)

def warn(logtype, message, group, user=None, meta=None):
    """Log a warning

    logtype: a string identifying this logging location, for example "lambda.handler.start"
    message: human readable message
    group: log group, for example technical, session or request
    user: some kind of user identifier
    meta: dictionary of free form data
    """
    span = LogSpan()
    span.warn(logtype, message, group, user, meta)

def error(logtype, message, group, user=None, meta=None):
    """Log an error

    logtype: a string identifying this logging location, for example "lambda.handler.start"
    message: human readable message
    group: log group, for example technical, session or request
    user: some kind of user identifier
    meta: dictionary of free form data
    """
    span = LogSpan()
    span.error(logtype, message, group, user, meta)
