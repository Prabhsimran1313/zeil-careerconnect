import json
import unittest
from unittest.mock import patch
import httpx
from google import genai
from google.genai import errors
from models import CareerRoadmap, PlanReview, InterviewFeedback
from ai_service import structured, error_message, generate_roadmap, scheduled_roadmap_schema
from sample import PROFILE, sample_roadmap


class GeminiRequestTests(unittest.TestCase):
    def test_selected_week_count_is_enforced_for_all_durations(self):
        for weeks in range(1, 5):
            with self.subTest(weeks=weeks):
                plan = sample_roadmap()
                plan.weeks = [plan.weeks[i % 3].model_copy(update={'week': i+1}) for i in range(weeks)]
                schema = scheduled_roadmap_schema(weeks)
                bounds = schema.model_json_schema()['properties']['weeks']
                self.assertEqual((bounds['minItems'], bounds['maxItems']), (weeks, weeks))
                with patch('ai_service.structured', return_value=plan) as request:
                    result = generate_roadmap(dict(PROFILE, weeks=weeks))
                self.assertEqual([w.week for w in result.weeks], list(range(1, weeks+1)))
                self.assertEqual(request.call_count, 1)

    def test_wrong_count_is_repaired_automatically(self):
        incomplete = sample_roadmap()
        incomplete.weeks = incomplete.weeks[:1]
        with patch('ai_service.structured', side_effect=[incomplete, sample_roadmap()]) as request:
            result = generate_roadmap(PROFILE)
        self.assertEqual(len(result.weeks), 3)
        self.assertEqual(request.call_count, 2)
        self.assertIn('Repair the previous formatting failure', request.call_args.args[0])

    def test_duplicate_and_out_of_order_numbers_keep_all_tasks(self):
        duplicate = sample_roadmap()
        duplicate.weeks[1].week = 1
        duplicate.weeks[2].week = 4
        titles = [task.title for week in duplicate.weeks for task in week.tasks]
        with patch('ai_service.structured', return_value=duplicate) as request:
            result = generate_roadmap(PROFILE)
        self.assertEqual([w.week for w in result.weeks], [1, 2, 3])
        self.assertEqual([task.title for week in result.weeks for task in week.tasks], titles)
        self.assertEqual(request.call_count, 1)
        shuffled = sample_roadmap()
        shuffled.weeks.reverse()
        with patch('ai_service.structured', return_value=shuffled):
            result = generate_roadmap(PROFILE)
        self.assertEqual(result.weeks[0].focus, sample_roadmap().weeks[0].focus)

    def test_repeated_incomplete_plans_stop_after_one_repair(self):
        incomplete = sample_roadmap()
        incomplete.weeks = incomplete.weeks[:1]
        with patch('ai_service.structured', return_value=incomplete) as request:
            with self.assertRaisesRegex(ValueError, 'after automatic repair'):
                generate_roadmap(PROFILE)
        self.assertEqual(request.call_count, 2)

    def test_quota_errors_do_not_trigger_a_repair_request(self):
        error = errors.APIError(429, {'error': {'code': 429, 'message': 'quota'}})
        with patch('ai_service.structured', side_effect=error) as request:
            with self.assertRaises(errors.APIError):
                generate_roadmap(PROFILE)
        self.assertEqual(request.call_count, 1)

    def test_real_sdk_serializes_json_schema_without_legacy_additional_properties(self):
        # Exercise the real SDK conversion rather than mocking generate_content.
        schemas = [CareerRoadmap, PlanReview, InterviewFeedback]
        for schema in schemas:
            with self.subTest(schema=schema.__name__):
                client = genai.Client(api_key='test-placeholder')
                with patch('ai_service.genai.Client', return_value=client), patch.object(
                    client._api_client, 'request', side_effect=RuntimeError('request intercepted')) as request:
                    with self.assertRaisesRegex(RuntimeError, 'request intercepted'):
                        structured('Request format diagnostic.', {}, schema)
                    data = request.call_args.args[2]
                    serialized = json.dumps(data)
                    self.assertNotIn('additional_properties', serialized)
                    config = data['generationConfig']
                    self.assertNotIn('responseSchema', config)
                    self.assertEqual(config['responseJsonSchema'], schema.model_json_schema())
                    self.assertFalse(config['responseJsonSchema']['additionalProperties'])

    def test_provider_failures_show_safe_specific_messages(self):
        for code, expected in [(400, 'HTTP 400'), (403, 'denied access'),
                (404, 'model was not found'), (429, 'quota'), (503, 'temporarily unavailable')]:
            with self.subTest(code=code):
                error = errors.APIError(code, {'error': {'code': code, 'message': 'private provider text'}})
                message = error_message(error)
                self.assertIn(expected, message)
                self.assertNotIn('private provider text', message)

    def test_connection_timeout_and_unexpected_errors_are_safe(self):
        self.assertIn('connect', error_message(httpx.ConnectError('private URL and key')))
        self.assertIn('too long', error_message(httpx.ReadTimeout('private URL and key')))
        self.assertNotIn('private', error_message(RuntimeError('private provider text')))
        self.assertNotIn('private', error_message(ValueError('private response text')))


if __name__ == '__main__':
    unittest.main()
