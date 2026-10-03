import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import httpx
from google.genai.errors import ServerError
from gemini_service import analyze_waste_image, answer_question, EcoSortError
from waste_utils import validate_analysis, count_categories, calculate_recyclability_score
from report_service import generate_report

DATA = {"items": [{"item_name": "Bottle", "material": "Plastic", "waste_category": "Recyclable", "disposal_method": "Check local recycling rules"}]}


class EcoSortTests(unittest.TestCase):
    def test_counts_score_and_empty(self):
        items = DATA["items"] + [dict(DATA["items"][0], waste_category="Hazardous")]
        self.assertEqual(calculate_recyclability_score(items, count_categories(items)), 50)
        self.assertEqual(calculate_recyclability_score([], count_categories([])), 0)
        self.assertEqual(len(count_categories([])), 5)

    def test_invalid_analysis(self):
        for data in [None, {}, {"items": [None]}, {"items": [{}]}, {"items": [dict(DATA["items"][0], waste_category="Other")]}]:
            with self.assertRaises(ValueError):
                validate_analysis(data)

    @patch("gemini_service.time.sleep")
    def test_timeout_is_bounded(self, sleep):
        client = MagicMock()
        client.models.generate_content.side_effect = httpx.ReadTimeout("private details")
        with self.assertRaisesRegex(EcoSortError, "timed out"):
            analyze_waste_image(client, None)
        self.assertEqual(client.models.generate_content.call_count, 3)

    @patch("gemini_service.time.sleep")
    def test_503_recovers(self, sleep):
        client = MagicMock()
        client.models.generate_content.side_effect = [ServerError(503, {"error": {"message": "Busy"}}), SimpleNamespace(text='{"items": []}')]
        self.assertEqual(analyze_waste_image(client, None), {"items": []})

    def test_malformed_json(self):
        client = MagicMock()
        client.models.generate_content.return_value.text = "not json"
        with self.assertRaisesRegex(EcoSortError, "incomplete"):
            analyze_waste_image(client, None)

    def test_chat_uses_context_and_history(self):
        client = MagicMock()
        client.models.generate_content.return_value.text = "Answer"
        answer_question(client, DATA, [{"role": "user", "content": "Earlier"}, {"role": "assistant", "content": "Reply"}], "Reuse?")
        contents = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("Bottle", contents[0].parts[0].text)
        self.assertEqual(contents[2].role, "model")
        self.assertEqual(contents[-1].parts[0].text, "Reuse?")

    def test_report(self):
        report = generate_report(DATA, [{"role": "assistant", "content": "Reuse it"}])
        self.assertIn("100.00%", report)
        self.assertIn("Reuse it", report)
        self.assertIn("Check local recycling rules", report)


if __name__ == "__main__":
    unittest.main()
