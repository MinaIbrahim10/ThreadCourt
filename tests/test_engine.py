import copy
import json
import unittest
from unittest.mock import patch
from threadcourt.engine import explore, replay, complete
from threadcourt.agents import investigate, Ollama


class EngineTests(unittest.TestCase):
    def test_counterexamples_replay(self):
        for scenario, kind in [('lost-update', 'lost-update'), ('lock-inversion', 'deadlock')]:
            with self.subTest(scenario=scenario):
                result = explore(scenario)
                self.assertTrue(result['exhaustive'])
                self.assertEqual(result['violation']['kind'], kind)
                state = replay(scenario, result['violation']['trace'])
                if kind == 'lost-update':
                    self.assertTrue(complete(state, scenario))
                    self.assertEqual(state.value, 1)
                else:
                    self.assertFalse(complete(state, scenario))
                    self.assertEqual(set(state.owners), {0, 1})

    def test_repairs_have_no_violation_in_finite_models(self):
        for scenario in ('lost-update', 'lock-inversion'):
            result = explore(scenario, fixed=True)
            self.assertTrue(result['exhaustive'])
            self.assertGreater(result['terminal_states'], 0)
            self.assertIsNone(result['violation'])

    def test_truncation_is_inconclusive(self):
        result = explore('lost-update', max_states=2)
        self.assertFalse(result['exhaustive'])
        self.assertEqual(result['verdict'], 'inconclusive')

    def test_tampered_trace_rejected(self):
        trace = copy.deepcopy(explore('lost-update')['violation']['trace'])
        trace[0]['value'] = 99
        with self.assertRaises(ValueError):
            replay('lost-update', trace)

    def test_blocked_schedule_rejected(self):
        trace = explore('lock-inversion')['violation']['trace']
        with self.assertRaises(ValueError):
            replay('lock-inversion', trace + [dict(trace[-1])])

    def test_real_threads_confirm_counter_failure_and_repair(self):
        from threadcourt.harness import counter_trial
        for _ in range(10):
            self.assertEqual(counter_trial()['actual'], 1)
            self.assertEqual(counter_trial(fixed=True)['actual'], 2)

    def test_invalid_inputs(self):
        for args in [('missing',), ('lost-update', False, 0), ('lost-update', False, 100001)]:
            with self.assertRaises(ValueError):
                explore(*args)

    def test_report_has_all_roles_and_replay(self):
        report = investigate('lost-update')
        self.assertEqual(len(report['agents']), 5)
        self.assertTrue(report['replayed'])
        self.assertIsNone(report['model'])

    def test_agent_failure_does_not_erase_evidence(self):
        class Broken:
            model = 'unavailable'
            def ask(self, *args):
                raise TimeoutError()
        report = investigate('lost-update', Broken())
        self.assertTrue(report['replayed'])
        self.assertEqual(sum(a['status'] == 'failed' for a in report['agents']), 4)

    def test_agent_sequence_receives_measured_evidence(self):
        class Fake:
            model = 'fake-test-only'
            def __init__(self): self.calls = []
            def ask(self, role, evidence):
                self.calls.append((role, evidence))
                return {'summary': 'Test response', 'caveats': []}
        client = Fake()
        report = investigate('lock-inversion', client)
        self.assertEqual([r for r, e in client.calls], ['investigator','adversary','repairer','judge'])
        self.assertTrue(client.calls[-1][1]['replayed'])
        self.assertEqual(report['after']['verdict'], 'no-violation-in-model')

    def test_ollama_payload_and_schema(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps({'message': {'content': json.dumps({'summary':'ok', 'caveats':[]})}}).encode()
        with patch('urllib.request.urlopen', return_value=Response()) as request:
            result = Ollama().ask('investigator', {'x':1})
            body = json.loads(request.call_args.args[0].data)
            self.assertEqual(body['model'], 'gemma4:e4b')
            self.assertFalse(body['stream'])
            self.assertFalse(body['think'])
            self.assertEqual(result['summary'], 'ok')

    def test_invalid_model_json_rejected(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self): return b'{"message":{"content":"{\\"summary\\":42,\\"caveats\\":[]}"}}'
        with patch('urllib.request.urlopen', return_value=Response()):
            with self.assertRaises(ValueError):
                Ollama().ask('judge', {})


if __name__ == '__main__': unittest.main()
