import unittest

from notcologger import LogSpan, debug, info, warn, error


class TestLogSpan(unittest.TestCase):
    def test_init(self):
        logger = LogSpan()
        logger2 = LogSpan('hsdkhkcsdlfjdlfjzlc')

    def test_annotate(self):
        # It works
        logger = LogSpan()
        logger.annotate(foo='bar', baz=123)

        # And it must fail right when fed something that is not serializable to JSON
        with self.assertRaises(TypeError):
            logger.annotate(ellipsis=Ellipsis)

        logger.info('foo', 'bar', 'session')

    def test_plain_debug(self):
        debug('test', 'message', 'technical')

    def test_logger_debug(self):
        logger = LogSpan('fake-id')
        logger.debug('test', 'message', 'technical')

    def test_plain_info(self):
        info('test', 'message', 'technical', 'user', {'foo': 'bar'})

    def test_logger_info(self):
        logger = LogSpan()
        logger.info('test', 'message', 'technical', 'user', {'foo': 'bar'})

    def test_plain_warn(self):
        warn('test', 'message', 'technical', 'user', {'foo': 'bar'})

    def test_logger_warn(self):
        logger = LogSpan()
        logger.warn('test', 'message', 'technical', 'user', {'foo': 'bar'})

    def test_plain_error(self):
        error('test', 'message', 'technical', 'user', {'foo': 'bar'})

    def test_logger_error(self):
        logger = LogSpan()
        logger.error('test', 'message', 'technical', 'user', {'foo': 'bar'})
