import asyncio
from contextlib import redirect_stdout
import io
import json
import unittest
from unittest.mock import patch

from notcologger import ExceptionSpan, LogSpan, debug, error, info, log_context, warn


def entries(output):
    return [json.loads(line) for line in output.getvalue().splitlines()]


class TestLogContext(unittest.TestCase):
    def setUp(self):
        self.output = io.StringIO()
        self.enterContext(redirect_stdout(self.output))
        self.enterContext(patch.dict('os.environ', {'NOTCO_LOGLEVEL': 'debug'}))

    def test_all_module_functions_and_event_precedence(self):
        with log_context('request', meta={'service': 'billing', 'key': 'context'}):
            for method in (debug, info, warn, error):
                method('event', 'message', 'technical', meta={'key': 'event'})
        for entry in entries(self.output):
            self.assertEqual(entry['rid'], 'request')
            self.assertEqual(entry['meta'], {'service': 'billing', 'key': 'event'})
            self.assertEqual(entry['user'], 'SYSTEM')
        self.assertEqual(len(entries(self.output)), 4)

    def test_generated_id_and_nested_restoration(self):
        with log_context(meta={'outer': True, 'key': 'outer'}):
            info('outer', 'message', 'technical')
            with log_context(meta={'key': 'inner'}):
                info('inherited', 'message', 'technical')
            with log_context('other'):
                info('other', 'message', 'technical')
            info('restored', 'message', 'technical')
        rows = entries(self.output)
        self.assertTrue(rows[0]['rid'])
        self.assertEqual(rows[0]['rid'], rows[1]['rid'])
        self.assertEqual(rows[0]['rid'], rows[3]['rid'])
        self.assertEqual(rows[2]['rid'], 'other')
        self.assertEqual(rows[1]['meta'], {'outer': True, 'key': 'inner'})
        self.assertEqual(rows[3]['meta'], {'outer': True, 'key': 'outer'})

    def test_cleanup_and_legacy_defaults(self):
        with self.assertRaises(RuntimeError):
            with log_context('request', meta={'private': True}):
                raise RuntimeError('failed')
        info('one', 'message', 'technical')
        info('two', 'message', 'technical')
        one, two = entries(self.output)
        self.assertNotEqual(one['rid'], two['rid'])
        self.assertNotEqual(one['rid'], 'request')
        self.assertNotIn('meta', one)

    def test_metadata_snapshot_at_entry(self):
        metadata = {'nested': {'items': ['original']}}
        scope = log_context('request', meta=metadata)
        metadata['before'] = True
        with scope:
            metadata['nested']['items'].append('changed')
            info('event', 'message', 'technical')
        self.assertEqual(entries(self.output)[0]['meta'], {
            'nested': {'items': ['original']}, 'before': True})

    def test_invalid_context_leaves_parent_unchanged(self):
        with log_context('parent'):
            for arguments, exception in (({'meta': {'bad': object()}}, TypeError),
                                         ({'meta': []}, TypeError),
                                         ({'requestId': ''}, ValueError)):
                with self.subTest(arguments=arguments), self.assertRaises(exception):
                    with log_context(**arguments):
                        self.fail('invalid context was entered')
            info('event', 'message', 'technical')
        self.assertEqual(entries(self.output)[0]['rid'], 'parent')

    def test_explicit_spans_stay_independent(self):
        with log_context('ambient', meta={'ambient': True}):
            LogSpan('explicit').info('explicit', 'message', 'technical')
            generated = LogSpan()
            generated.info('generated', 'message', 'technical')
            with self.assertRaises(ValueError):
                with ExceptionSpan('failure', 'message', 'technical'):
                    info('module', 'message', 'technical')
                    raise ValueError('original')
        rows = entries(self.output)
        self.assertEqual(rows[0]['rid'], 'explicit')
        self.assertNotEqual(rows[1]['rid'], 'ambient')
        self.assertEqual(rows[2]['rid'], 'ambient')
        self.assertNotEqual(rows[3]['rid'], 'ambient')
        for row in (rows[0], rows[1], rows[3]):
            self.assertNotIn('ambient', row.get('meta', {}))


class TestAsyncLogContext(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.output = io.StringIO()
        self.enterContext(redirect_stdout(self.output))
        self.enterContext(patch.dict('os.environ', {'NOTCO_LOGLEVEL': 'debug'}))

    async def test_concurrent_requests(self):
        async def request(name):
            with log_context(name, meta={'request': name}):
                info(name, 'before', 'technical')
                await asyncio.sleep(0)
                with log_context(meta={'child': name}):
                    await asyncio.sleep(0)
                    info(name, 'nested', 'technical')
                info(name, 'after', 'technical')
        await asyncio.gather(request('one'), request('two'))
        rows = entries(self.output)
        self.assertEqual(len(rows), 6)
        for row in rows:
            self.assertEqual(row['rid'], row['type'])
            self.assertEqual(row['meta']['request'], row['type'])
            self.assertEqual('child' in row['meta'], row['message'] == 'nested')

    async def test_child_inherits_snapshot_beyond_parent_scope(self):
        ready = asyncio.Event()

        async def child():
            await ready.wait()
            info('child', 'message', 'technical')
            with log_context('child-only'):
                info('nested', 'message', 'technical')

        with log_context('parent', meta={'parent': True}):
            task = asyncio.create_task(child())
            with log_context('later'):
                info('later', 'message', 'technical')
        ready.set()
        await task
        info('outside', 'message', 'technical')
        rows = entries(self.output)
        self.assertEqual(rows[1]['rid'], 'parent')
        self.assertEqual(rows[1]['meta'], {'parent': True})
        self.assertEqual(rows[2]['rid'], 'child-only')
        self.assertNotIn('meta', rows[3])

    async def test_cancellation_restores_context(self):
        started = asyncio.Event()

        async def worker():
            try:
                with log_context('cancelled', meta={'private': True}):
                    started.set()
                    await asyncio.Event().wait()
            except asyncio.CancelledError:
                info('cleanup', 'message', 'technical')
                raise

        with log_context('parent'):
            task = asyncio.create_task(worker())
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        row, = entries(self.output)
        self.assertEqual(row['rid'], 'parent')
        self.assertNotIn('meta', row)

    async def test_to_thread_propagates_context(self):
        with log_context('thread', meta={'service': 'billing'}):
            await asyncio.to_thread(info, 'event', 'message', 'technical')
        row, = entries(self.output)
        self.assertEqual(row['rid'], 'thread')
        self.assertEqual(row['meta'], {'service': 'billing'})
