"""Orchestration/authority checks. Fixtures are not evidence of real agent repair."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'loop'))
import common
import runner
spec = importlib.util.spec_from_file_location('doom_mcp', ROOT / 'loop/mcp/server.py')
mcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp)


class Authority(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ('platform', 'web', 'tests', 'loop'):
            (self.root / name).mkdir()
        (self.root / 'tests/acceptance.py').write_text('protected\n')
        self.run = self.root / 'artifacts/runs/test'

    def tearDown(self):
        self.temp.cleanup()

    def server(self, role):
        return mcp.Server(self.root, role, self.run, self.run / role)

    def test_coder_denied_protected_paths_and_traversal(self):
        server = self.server('coder')
        for name in ('tests/acceptance.py', 'loop/runner.py', 'build.sh', '../escape.c', '/tmp/escape.c', 'platform/../tests/acceptance.py', 'web/.env'):
            with self.subTest(path=name), self.assertRaises(PermissionError):
                server.call('write_file', {'path': name, 'content': 'changed'})
        self.assertEqual((self.root / 'tests/acceptance.py').read_text(), 'protected\n')

    def test_symlink_and_hardlink_escape_denied(self):
        (self.root / 'web/link.js').symlink_to(self.root / 'tests/acceptance.py')
        (self.root / 'web/hard.js').hardlink_to(self.root / 'tests/acceptance.py')
        for name in ('web/link.js', 'web/hard.js'):
            with self.subTest(path=name), self.assertRaises(PermissionError):
                self.server('coder').call('write_file', {'path': name, 'content': 'changed'})

    def test_roles_have_different_capabilities(self):
        for role in ('reviewer', 'tester'):
            with self.assertRaises(PermissionError):
                self.server(role).call('write_file', {'path': 'web/index.html', 'content': 'x'})
        with self.assertRaises(PermissionError):
            self.server('coder').call('verify', {})
        self.server('coder').call('write_file', {'path': 'web/main.js', 'content': 'valid'})
        self.assertEqual((self.root / 'web/main.js').read_text(), 'valid')

    def test_tester_cannot_pass_without_execution(self):
        with self.assertRaises(ValueError):
            self.server('tester').call('handoff', {'verdict': 'PASS', 'summary': 'Trust me'})

    def test_handoffs_immutable(self):
        server = self.server('reviewer')
        server.call('handoff', {'verdict': 'FAIL', 'summary': 'Missing evidence'})
        with self.assertRaises(ValueError):
            server.call('handoff', {'verdict': 'PASS', 'summary': 'Changed mind'})

    def test_unknown_and_extra_arguments_denied(self):
        for name, args in [('shell', {'command': 'true'}), ('list_files', {'command': 'true'})]:
            self.assertTrue(self.server('coder').dispatch({'method': 'tools/call', 'params': {'name': name, 'arguments': args}})['isError'])

    def test_stdio_protocol_and_denial(self):
        invocation = self.run / 'protocol'
        messages = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'write_file', 'arguments': {'path': 'tests/acceptance.py', 'content': 'bad'}}}]
        result = subprocess.run([sys.executable, str(ROOT / 'loop/mcp/server.py'), '--root', str(self.root), '--role', 'coder', '--run', str(self.run), '--invocation', str(invocation)], input='\n'.join(map(json.dumps, messages)) + '\n', text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([r['id'] for r in replies], [1, 2, 3])
        self.assertTrue(replies[-1]['result']['isError'])
        self.assertIn('tools', replies[0]['result']['capabilities'])


class Orchestration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run = self.root / 'artifacts/runs/fixture'
        self.run.mkdir(parents=True)
        self.digest = 'source-1'
        self.state = {'source_digest': self.digest, 'completed': [], 'attempts': {}, 'usage': [], 'charged_usd': 0, 'seconds': 0, 'history': [], 'events': []}
        self.config = {'max_retries': 3, 'max_seconds_per_run': 60, 'max_seconds_per_agent': 10, 'max_budget_usd_per_agent': 2, 'max_budget_usd_per_run': 30, 'tasks': [{'id': 'one', 'description': ''}, {'id': 'two', 'description': ''}]}
        self.calls = []
        self.fail = False
        self.interrupt = False
        self.patches = [patch.object(runner, 'ROOT', self.root), patch.object(runner, 'snapshot', lambda: {'digest': self.digest}), patch.object(runner, 'invoke', self.invoke)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def invoke(self, role, task, attempt, *args):
        self.calls.append((task['id'], role))
        directory = attempt / role
        directory.mkdir()
        (directory / 'sentinel').write_text('preserve')
        if self.interrupt:
            self.interrupt = False
            raise KeyboardInterrupt()
        common.save(directory / 'result.json', {'is_error': False, 'subtype': 'success', 'total_cost_usd': 0.1, 'usage': {'input_tokens': 12}})
        common.save(directory / 'handoff.json', {'role': role, 'verdict': 'FAIL' if self.fail else ('DONE' if role == 'coder' else 'PASS'), 'source_digest': self.digest})
        return directory, {'returncode': 0, 'seconds': 0.01}

    def test_all_tasks_run_before_success(self):
        runner.run_loop(self.run, self.state, self.config)
        self.assertEqual(self.state['status'], 'SUCCESS')
        self.assertEqual(len(self.calls), 6)
        self.assertEqual(self.state['completed'], ['one', 'two'])
        self.assertAlmostEqual(self.state['charged_usd'], 0.6)

    def test_failure_stalls_and_never_completes(self):
        self.fail = True
        runner.run_loop(self.run, self.state, self.config)
        self.assertEqual(self.state['status'], 'STALLED')
        self.assertEqual(self.state['completed'], [])
        self.assertEqual(len(list(self.run.glob('one-*'))), 2)

    def test_budget_stops_before_launch(self):
        self.config['max_budget_usd_per_run'] = 1
        runner.run_loop(self.run, self.state, self.config)
        self.assertEqual(self.state['status'], 'EXHAUSTED')
        self.assertEqual(self.calls, [])

    def test_interrupt_resume_retains_attempt_and_reservation(self):
        self.interrupt = True
        runner.run_loop(self.run, self.state, self.config)
        self.assertEqual(self.state['status'], 'INTERRUPTED')
        self.assertEqual(self.state['charged_usd'], 2)
        original = next(self.run.glob('one-*/coder/sentinel'))
        # Restore from disk, as a fresh runner process would.
        resumed = json.loads((self.run / 'state.json').read_text())
        runner.run_loop(self.run, resumed, self.config)
        self.assertEqual(resumed['status'], 'SUCCESS')
        self.assertEqual(original.read_text(), 'preserve')
        self.assertEqual(resumed['attempts']['one'], 2)
        self.assertAlmostEqual(resumed['charged_usd'], 2.6)

    def test_changed_source_invalidates_completed_tasks(self):
        self.state['completed'] = ['one']
        self.digest = 'source-2'
        runner.run_loop(self.run, self.state, self.config)
        self.assertEqual(self.calls[0], ('one', 'coder'))
        self.assertEqual(self.state['events'][0]['type'], 'source_changed')

    def test_pass_text_cannot_override_structured_failure(self):
        directory = self.run / 'verdict'
        directory.mkdir()
        common.save(directory / 'result.json', {'is_error': True, 'subtype': 'success', 'result': 'VERDICT: PASS'})
        common.save(directory / 'handoff.json', {'role': 'reviewer', 'verdict': 'PASS', 'source_digest': self.digest})
        self.assertFalse(runner.accepted('reviewer', directory, self.digest))


if __name__ == '__main__':
    unittest.main()
