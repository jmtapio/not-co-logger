import unittest

from notcologger import LogSpan, ExceptionSpan, debug, info, warn, error


class MockOutput:
    def write(self, output):
        self.output = output

    def flush(self):
        pass


class PatchedLogSpan(LogSpan):
    def _make_timestamp(self):
        return "faketimestamp"


class TestLogSpan(unittest.TestCase):
    def test_init(self):
        logger = LogSpan()
        logger2 = LogSpan('hsdkhkcsdlfjdlfjzlc')

    def test_annotate(self):
        # It works
        logger = LogSpan()
        logger._stdout = MockOutput()
        logger.annotate(foo='bar', baz=123)

        # And it must fail right when fed something that is not serializable to JSON
        with self.assertRaises(TypeError):
            logger.annotate(ellipsis=Ellipsis)

        logger.info('foo', 'bar', 'session')

        self.assertIn('"type": "foo", "message": "bar", "group": "session", "user": "SYSTEM"}',
                      logger._stdout.output)

    def test_plain_debug(self):
        debug('test', 'message', 'technical')

    def test_logger_debug(self):
        logger = PatchedLogSpan('fake-id')
        logger._stdout = MockOutput()
        logger.debug('test', 'message', 'technical')
        self.assertEqual(
            logger._stdout.output,
            '{"timestamp": "faketimestamp", "level": "debug", "rid": "fake-id", "type": "test", "message": "message", "group": "technical", "user": "SYSTEM"}\n')

    def test_plain_info(self):
        info('test', 'message', 'technical', 'user', {'foo': 'bar'})

    def test_logger_info(self):
        logger = PatchedLogSpan('fake-id')
        logger._stdout = MockOutput()
        logger.info('test', 'message', 'technical', 'user', {'foo': 'bar'})
        self.assertEqual(
            logger._stdout.output,
            '{"timestamp": "faketimestamp", "level": "info", "rid": "fake-id", "type": "test", "message": "message", "group": "technical", "user": "user", "meta": {"foo": "bar"}}\n')

    def test_plain_warn(self):
        warn('test', 'message', 'technical', 'user', {'foo': 'bar'})

    def test_logger_warn(self):
        logger = PatchedLogSpan('fake-id')
        logger._stdout = MockOutput()
        logger.warn('test', 'message', 'technical', 'user', {'foo': 'bar'})
        self.assertEqual(
            logger._stdout.output,
            '{"timestamp": "faketimestamp", "level": "warning", "rid": "fake-id", "type": "test", "message": "message", "group": "technical", "user": "user", "meta": {"foo": "bar"}}\n')

    def test_plain_error(self):
        error('test', 'message', 'technical', 'user', {'foo': 'bar'})

    def test_logger_error(self):
        logger = PatchedLogSpan('fake-id')
        logger._stdout = MockOutput()
        logger.error('test', 'message', 'technical', 'user', {'foo': 'bar'})
        self.assertEqual(
            logger._stdout.output,
            '{"timestamp": "faketimestamp", "level": "error", "rid": "fake-id", "type": "test", "message": "message", "group": "technical", "user": "user", "meta": {"foo": "bar"}}\n')

    def test_bytes(self):
        logger = PatchedLogSpan('fake-id')
        logger._stdout = MockOutput()
        logger.error('bytestest', 'message', 'technical', 'user', dict(foo=b'bar'))
        self.assertEqual(
            logger._stdout.output,
            '{"timestamp": "faketimestamp", "level": "error", "rid": "fake-id", "type": "bytestest", "message": "message", "group": "technical", "user": "user", "meta": {"foo": "bar"}}\n')

    def test_exception(self):
        logger = PatchedLogSpan('fake-id')
        logger._stdout = MockOutput()
        e = ValueError('some invalid value')
        logger.error('exceptiontest', 'message', 'session', 'user', dict(exc=e))
        self.assertEqual(
            logger._stdout.output,
            '{"timestamp": "faketimestamp", "level": "error", "rid": "fake-id", "type": "exceptiontest", "message": "message", "group": "session", "user": "user", "meta": {"exc": "ValueError(\'some invalid value\')"}}\n')


class FakeError(Exception):
    pass


class TestExceptionSpan(unittest.TestCase):
    def test_basic(self):
        try:
            with ExceptionSpan('foo', 'bar', 'technical', requestId='fake-id') as log:
                log._stdout = MockOutput()
                log._make_timestamp = PatchedLogSpan()._make_timestamp
                raise FakeError("valueerror")
        except FakeError:
            pass
        self.assertEqual(log._stdout.output,
                         '{"timestamp": "faketimestamp", "level": "error", "rid": "fake-id", "type": "foo", "message": "bar", "group": "technical", "user": "SYSTEM", "meta": {"exc_type": "FakeError", "exc_val": "(\'valueerror\',)"}}\n')

    def test_nofail(self):
        try:
            with ExceptionSpan('foo', 'bar', 'technical', requestId='fake-id') as log:
                log._stdout = MockOutput()
                log._stdout.output = 'nothing'
                pass
            self.assertEqual(log._stdout.output, "nothing")
        except FakeError:
            pass
