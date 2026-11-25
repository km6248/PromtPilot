import unittest
from app import app, analyze_prompt


class PromptPilotTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PromptPilot", response.data)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "healthy")

    def test_valid_analysis(self):
        response = self.client.post("/analyze", json={
            "prompt": "Explain AI for college students. Give 5 examples in a bullet list. Use simple language and keep it under 300 words."
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["score"], 100)
        self.assertEqual(len(data["checks"]), 5)
        self.assertIn("improved", data)

    def test_short_prompt(self):
        response = self.client.post("/analyze", json={"prompt": "hi"})
        self.assertEqual(response.status_code, 400)

    def test_wrong_content_type(self):
        response = self.client.post("/analyze", data="prompt=hello")
        self.assertEqual(response.status_code, 415)

    def test_prompt_type(self):
        response = self.client.post("/analyze", json={"prompt": 123})
        self.assertEqual(response.status_code, 400)

    def test_too_long(self):
        response = self.client.post("/analyze", json={"prompt": "a" * 5001})
        self.assertEqual(response.status_code, 413)

    def test_untrusted_text_is_not_interpreted(self):
        prompt = "<script>alert(1)</script> explain this for students in a bullet list"
        response = self.client.post("/analyze", json={"prompt": prompt})
        self.assertEqual(response.status_code, 200)
        self.assertIn("<script>", response.get_json()["improved"])

    def test_security_headers(self):
        response = self.client.get("/")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")


if __name__ == "__main__":
    unittest.main()
