import copy
import importlib.util
import os
import unittest

from evaluation.sandbox import CommandResult, DockerSandbox


class RecordingSandbox:
    def __init__(self, output=b'ok'):
        self.output = output
        self.calls = []
        self.closed = False

    def run(self, command, stdin=''):
        self.calls.append((command, stdin))
        return CommandResult(0, self.output, False, False, 0.01)

    def close(self):
        self.closed = True


class SessionTests(unittest.TestCase):
    def session_type(self):
        self.assertIsNotNone(importlib.util.find_spec('evaluation.session'),
                             'runner needs a bounded tool-session interface')
        from evaluation.session import ToolSession
        return ToolSession

    def test_exact_requests_and_results_are_recorded_without_caller_aliasing(self):
        sandbox = RecordingSandbox()
        session = self.session_type()(sandbox)
        request = {'command': ['python', '--version'], 'stdin': ''}
        original = copy.deepcopy(request)
        result = session.execute(request)
        request['command'].append('changed later')
        self.assertEqual(result.output, 'ok')
        self.assertEqual(session.observations[0]['request'], original)
        self.assertEqual(session.observations[0]['output'], 'ok')
        self.assertEqual(session.observations[0]['call_id'], session.session_id + ':1')
        self.assertNotEqual(session.session_id, self.session_type()(RecordingSandbox()).session_id)

    def test_call_limit_is_terminal_and_prevents_extra_execution(self):
        sandbox = RecordingSandbox()
        session = self.session_type()(sandbox, max_calls=1)
        session.execute({'command': ['true']})
        with self.assertRaisesRegex(ValueError, 'call limit'):
            session.execute({'command': ['echo', 'must not run']})
        self.assertEqual(len(sandbox.calls), 1)
        self.assertTrue(sandbox.closed)
        self.assertEqual(len(session.observations), 2)
        self.assertIn('call limit', session.observations[-1]['error'])
        with self.assertRaisesRegex(ValueError, 'terminated'):
            session.execute({'command': ['true']})
        self.assertEqual(len(session.observations), 2)

    def test_invalid_requests_fail_before_sandbox_and_leave_rejection_trace(self):
        for request in ({'command': 'echo bad'}, {'command': []},
                        {'command': ['echo'], 'stdin': 3},
                        {'command': ['echo'], 'secret': 'unknown'},
                        {'command': ['a\x00b']}, ['not an object']):
            with self.subTest(request=request):
                sandbox = RecordingSandbox()
                session = self.session_type()(sandbox)
                with self.assertRaises(ValueError):
                    session.execute(request)
                self.assertEqual(sandbox.calls, [])
                self.assertTrue(sandbox.closed)
                self.assertTrue(session.observations[-1]['error'])

    def test_cumulative_input_and_output_limits_use_bytes(self):
        for limit in ('max_input_bytes', 'max_output_bytes'):
            with self.subTest(limit=limit):
                sandbox = RecordingSandbox(b'x' * 40)
                session = self.session_type()(sandbox, **{limit: 70})
                session.execute({'command': ['echo', '\u00e9' * 10]})
                with self.assertRaisesRegex(ValueError, 'byte limit'):
                    session.execute({'command': ['echo', '\u00e9' * 10]})
                self.assertEqual(len(sandbox.calls), 1 if limit == 'max_input_bytes' else 2)
                self.assertTrue(sandbox.closed)
                self.assertTrue(session.observations[-1]['error'])

    def test_invalid_limits_rejected_before_execution(self):
        for options in ({'max_calls': True}, {'max_calls': 0}, {'max_calls': 65},
                        {'max_input_bytes': 0}, {'max_output_bytes': float('inf')}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.session_type()(RecordingSandbox(), **options)


@unittest.skipUnless(os.environ.get('CODE_COMMENTS_DOCKER') == '1', 'opt-in Docker integration')
class DockerSessionTests(unittest.TestCase):
    def test_real_tool_outputs_are_recorded_and_budget_stops_container(self):
        from evaluation.session import ToolSession
        with DockerSandbox({'current.txt': 'visible now'}) as sandbox:
            session = ToolSession(sandbox, max_calls=1)
            result = session.execute({'command': ['python', '-I', '-B', '-c',
                                                  "from pathlib import Path; print(Path('current.txt').read_text())"]})
            self.assertEqual(result.output.strip(), 'visible now')
            with self.assertRaisesRegex(ValueError, 'call limit'):
                session.execute({'command': ['python', '--version']})
            self.assertTrue(sandbox.closed)


if __name__ == '__main__':
    unittest.main()
