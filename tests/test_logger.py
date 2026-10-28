import io
import json
import os
import unittest
from unittest.mock import patch

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

        entry = json.loads(logger._stdout.output)
        self.assertEqual(entry['meta'], {'foo': 'bar', 'baz': 123})
        self.assertEqual(entry['user'], 'SYSTEM')

    def test_metadata_precedence_and_no_mutation(self):
        logger = LogSpan()
        logger._stdout = io.StringIO()
        logger.annotate(shared='annotation', persistent=True)
        exc = ValueError('bad')
        metadata = {'shared': 'event', 'bytes': b'hello', 'exc': exc}
        logger.info('test', 'message', 'technical', meta=metadata)
        entry = json.loads(logger._stdout.getvalue())
        self.assertEqual(entry['meta'], {
            'shared': 'event', 'persistent': True,
            'bytes': 'hello', 'exc': repr(exc)})
        self.assertEqual(metadata['bytes'], b'hello')
        self.assertIs(metadata['exc'], exc)
        self.assertEqual(logger.annotation, {'shared': 'annotation', 'persistent': True})

    def test_level_filtering(self):
        levels = ('debug', 'info', 'warning', 'error')
        for configured in (None, 'invalid') + levels:
            with self.subTest(configured=configured), patch.dict(os.environ):
                if configured is None:
                    os.environ.pop('NOTCO_LOGLEVEL', None)
                else:
                    os.environ['NOTCO_LOGLEVEL'] = configured
                logger = LogSpan()
                logger._stdout = io.StringIO()
                for method in (logger.debug, logger.info, logger.warn, logger.error):
                    method('test', 'message', 'technical')
                emitted = [json.loads(line)['level']
                           for line in logger._stdout.getvalue().splitlines()]
                expected = levels[levels.index(configured):] if configured in levels else levels
                self.assertEqual(emitted, list(expected))

    def test_ordinary_logging_errors_propagate(self):
        logger = LogSpan()
        logger._stdout = io.StringIO()
        with self.assertRaises(TypeError):
            logger.info('test', 'message', 'technical', meta={'bad': object()})
        with patch.object(logger._stdout, 'write', side_effect=OSError('write failed')):
            with self.assertRaises(OSError):
                logger.info('test', 'message', 'technical')

    def test_nonfinite_values_are_rejected_without_writing(self):
        logger = LogSpan()
        logger._stdout = io.StringIO()
        for value in (float('nan'), float('inf'), float('-inf')):
            for metadata in ({'value': value}, {'nested': [{'value': value}]}):
                with self.subTest(value=value, metadata=metadata):
                    with self.assertRaises(ValueError):
                        logger.info('test', 'message', 'technical', meta=metadata)
                    self.assertEqual(logger._stdout.getvalue(), '')
            with self.subTest(value=value, field='message'):
                with self.assertRaises(ValueError):
                    logger.info('test', value, 'technical')
                self.assertEqual(logger._stdout.getvalue(), '')

    def test_nonfinite_annotations_leave_existing_values_unchanged(self):
        logger = LogSpan()
        logger.annotate(existing='original')
        for value in (float('nan'), float('inf'), float('-inf')):
            for invalid in (value, {'nested': [value]}):
                with self.subTest(value=value, invalid=invalid):
                    with self.assertRaises(ValueError):
                        logger.annotate(existing='replacement', bad=invalid)
                    self.assertEqual(logger.annotation, {'existing': 'original'})

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

    def test_utf8(self):
        logger = PatchedLogSpan('fake-id')
        logger._stdout = MockOutput()
        logger.info('test', 'test', 'technical', 'user', {'föö': 'böö'})
        self.assertEqual(
                logger._stdout.output,
                '{"timestamp": "faketimestamp", "level": "info", "rid": "fake-id", "type": "test", "message": "test", "group": "technical", "user": "user", "meta": {"föö": "böö"}}\n')


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

    def test_metadata_is_preserved_and_copied(self):
        metadata = {'session': 'abc', 'exc_type': 'overridden'}
        span = ExceptionSpan('test', 'message', 'technical', meta=metadata)
        span.annotate(extra=True)
        self.assertNotIn('extra', metadata)
        span._stdout = io.StringIO()
        original = FakeError('original')
        with self.assertRaises(FakeError) as caught:
            with span:
                raise original
        self.assertIs(caught.exception, original)
        self.assertEqual(json.loads(span._stdout.getvalue())['meta'], {
            'session': 'abc', 'extra': True,
            'exc_type': 'FakeError', 'exc_val': "('original',)"})

    def test_logging_failures_preserve_original_exception(self):
        for failure in ('serialization', 'write', 'flush'):
            with self.subTest(failure=failure):
                span = ExceptionSpan('test', 'message', 'technical',
                                     meta={'bad': object()} if failure == 'serialization' else None)
                span._stdout = io.StringIO()
                original = FakeError('original')
                if failure != 'serialization':
                    setattr(span._stdout, failure, unittest.mock.Mock(side_effect=OSError(failure)))
                with self.assertRaises(FakeError) as caught:
                    with span:
                        raise original
                self.assertIs(caught.exception, original)

    def test_nonfinite_metadata_preserves_original_exception(self):
        for value in (float('nan'), float('inf'), float('-inf')):
            with self.subTest(value=value):
                span = ExceptionSpan('test', 'message', 'technical',
                                     meta={'nested': [value]})
                span._stdout = io.StringIO()
                original = FakeError('original')
                with self.assertRaises(FakeError) as caught:
                    with span:
                        raise original
                self.assertIs(caught.exception, original)
                self.assertEqual(span._stdout.getvalue(), '')

    def test_nofail(self):
        try:
            with ExceptionSpan('foo', 'bar', 'technical', requestId='fake-id') as log:
                log._stdout = MockOutput()
                log._stdout.output = 'nothing'
                pass
            self.assertEqual(log._stdout.output, "nothing")
        except FakeError:
            pass
