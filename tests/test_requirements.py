import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PIL import Image
from streamlit.testing.v1 import AppTest

from conversation import start_conversation, record_analysis, combined_analysis
from gemini_service import conversation_contents, summarize_conversation, EcoSortError
from image_utils import prepare_image
from report_service import generate_report
from tests.test_ecosort import DATA


def photo_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), "green").save(buffer, format="PNG")
    return buffer.getvalue()


class RequirementTests(unittest.TestCase):
    def test_image_limits_and_invalid_bytes(self):
        self.assertEqual(prepare_image(photo_bytes()).size, (16, 16))
        for content in [b"not an image", b"x" * (10 * 1024 * 1024 + 1)]:
            with self.assertRaises(ValueError):
                prepare_image(content)

    def test_photo_history_and_duplicate_counts(self):
        state = {"name": "Student"}
        start_conversation(state)
        image = prepare_image(photo_bytes())
        record_analysis(state, photo_bytes(), image, DATA)
        record_analysis(state, photo_bytes(), image, DATA)
        self.assertEqual(len(combined_analysis(state)["items"]), 1)
        record_analysis(state, b"second-file", image, DATA)
        self.assertEqual(len(combined_analysis(state)["items"]), 2)
        self.assertEqual(state["messages"][1]["kind"], "image")
        start_conversation(state)
        self.assertEqual(combined_analysis(state), {"items": []})
        self.assertEqual(len(state["messages"]), 1)

    def test_full_history_reaches_gemini(self):
        messages = [{"role": "user", "content": f"Question {i}"} for i in range(30)]
        contents = conversation_contents(DATA, messages)
        self.assertEqual(len(contents), 31)
        self.assertEqual(contents[1].parts[0].text, "Question 0")

    def test_summary_keeps_totals_and_images_out_of_email(self):
        state = {"name": "Student"}
        start_conversation(state)
        record_analysis(state, photo_bytes(), prepare_image(photo_bytes()), DATA)
        client = MagicMock()
        client.models.generate_content.return_value.text = "Reuse where safe."
        summary = summarize_conversation(client, DATA, state["messages"])
        contents = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("100.00%", contents[-1].parts[0].text)
        self.assertIsNotNone(contents[1].parts[0].inline_data)
        report = generate_report(DATA, state["messages"], summary, "Student")
        self.assertIn("Prepared for: Student", report)
        self.assertIn("AI CONVERSATION SUMMARY", report)
        self.assertIn("[Waste photo uploaded]", report)
        self.assertNotIn("\\xff", report)


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()
        self.create = patch("gemini_service.create_client", return_value=self.client)
        self.create.start()
        self.addCleanup(self.create.stop)
        self.app = AppTest.from_file("app.py", default_timeout=10).run()

    def onboard(self):
        self.app.text_input[0].set_value("Student")
        self.app.text_input[1].set_value("student@example.com")
        self.button("Let's go").click().run()
        self.assertFalse(self.app.exception)

    def button(self, label):
        return next(b for b in self.app.button if b.label == label)

    def ask(self, text="", photo=None):
        user_input = SimpleNamespace(text=text, files=[photo] if photo else [])
        with patch("streamlit.chat_input", side_effect=[user_input, None]):
            self.app.run()
        self.assertFalse(self.app.exception)

    def test_onboarding_and_report_gating(self):
        self.button("Let's go").click().run()
        self.assertTrue(self.app.warning)
        self.onboard()
        self.assertIn("Hi Student", self.app.chat_message[0].markdown[0].value)
        self.assertTrue(self.button("Generate report").disabled)
        self.assertTrue(self.button("Send EcoSort Report").disabled)

    def test_text_chat_cached_client_summary_and_email(self):
        self.onboard()
        with patch("gemini_service.answer_question", return_value="Reuse it."):
            self.ask("Can I reuse cardboard?")
            self.ask("What about wet cardboard?")
        self.assertEqual(self.create.call_count, 1)
        self.assertEqual(len(self.app.session_state.messages), 5)
        with patch("gemini_service.summarize_conversation", return_value="Cardboard guidance.") as summary, patch("email_service.send_report") as send:
            self.button("Send EcoSort Report").click().run()
            self.assertFalse(self.app.exception)
            send.assert_called_once_with("student@example.com", self.app.session_state.report)
            self.assertEqual(len(summary.call_args.args[2]), 5)
            self.button("Send EcoSort Report").click().run()
            self.assertEqual(send.call_count, 1)
        self.assertEqual(len(self.app.get("download_button")), 1)
        self.button("Start new conversation").click().run()
        self.assertIsNone(self.app.session_state.report)
        self.assertEqual(len(self.app.session_state.messages), 1)
        self.assertEqual(self.app.session_state.email, "student@example.com")

    def test_photo_only_and_photo_with_text(self):
        self.onboard()
        photo = SimpleNamespace(getvalue=photo_bytes)
        with patch("gemini_service.analyze_waste_image", return_value=DATA), patch("gemini_service.answer_question", return_value="Rinse it.") as answer:
            self.ask(photo=photo)
            answer.assert_not_called()
            self.assertEqual(self.app.metric[0].value, "1")
            self.ask("How should I sort this?", photo)
            answer.assert_called_once()
        self.assertEqual(self.app.metric[0].value, "1")
        self.assertTrue(any(m.get("kind") == "image" for m in self.app.session_state.messages))

    def test_failure_preserves_conversation_and_prevents_email(self):
        self.onboard()
        with patch("gemini_service.answer_question", side_effect=EcoSortError("Try again.")):
            self.ask("Can I recycle paper?")
        self.assertEqual(len(self.app.session_state.messages), 1)
        self.assertTrue(self.app.warning)
        with patch("gemini_service.answer_question", return_value="Check local rules."):
            self.ask("Can I recycle paper?")
        with patch("gemini_service.summarize_conversation", side_effect=EcoSortError("Summary unavailable.")), patch("email_service.send_report") as send:
            self.button("Send EcoSort Report").click().run()
            send.assert_not_called()
        self.assertIsNone(self.app.session_state.report)
        self.assertFalse(self.app.exception)
