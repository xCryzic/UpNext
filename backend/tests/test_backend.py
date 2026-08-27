import tempfile
import unittest
from pathlib import Path

from app import create_app


class TestConfig:
    SECRET_KEY = "test-secret"
    DATABASE_PATH = Path(tempfile.gettempdir()) / "upnext-test.sqlite"
    FRONTEND_ORIGIN = "http://localhost:5173"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    EXPOSE_DB_INFO = False


class BackendTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = TestConfig.DATABASE_PATH
        if cls.db_path.exists():
            cls.db_path.unlink()

    def setUp(self):
        if self.db_path.exists():
            self.db_path.unlink()
        self.app = create_app(TestConfig)
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.client.post("/api/auth/logout")

    def signup(self, email="creator@example.com", password="correct-horse"):
        return self.client.post("/api/auth/signup", json={"email": email, "password": password})

    def create_profile(self, username="maker"):
        return self.client.post("/api/creator", json={
            "display_name": "A Maker", "username": username, "bio": "Building useful things.",
            "categories": ["Developer"], "skills": ["Python"], "looking_for": ["Collaboration"],
        })

    def test_auth_lifecycle(self):
        self.assertEqual(self.signup().status_code, 201)
        self.assertEqual(self.signup().status_code, 409)
        self.assertEqual(self.client.get("/api/auth/me").json["user"]["email"], "creator@example.com")
        self.client.post("/api/auth/logout")
        self.assertIsNone(self.client.get("/api/auth/me").json["user"])
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "creator@example.com", "password": "wrong-pass"}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "creator@example.com", "password": "correct-horse"}).status_code, 200)

    def test_creator_profile_and_duplicate_username(self):
        self.signup()
        self.assertEqual(self.create_profile().status_code, 201)
        self.assertEqual(self.client.post("/api/creator", json={"display_name": "Other", "username": "other"}).status_code, 409)
        updated = self.client.patch("/api/creator", json={"bio": "Updated bio"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["creator"]["bio"], "Updated bio")

        self.client.post("/api/auth/logout")
        self.signup("second@example.com")
        self.assertEqual(self.create_profile("maker").status_code, 409)

    def test_publishability_requires_project_and_social(self):
        self.signup()
        self.create_profile()
        status = self.client.get("/api/creator/status").json
        self.assertFalse(status["publishable"])
        self.assertIn("project", status["missing"])
        self.assertIn("social_account", status["missing"])

        social = self.client.post("/api/creator/socials", json={"platform": "GitHub", "username": "maker", "profile_url": "https://github.com/maker"})
        self.assertEqual(social.status_code, 201)
        project = self.client.post("/api/creator/projects", json={"title": "Tool", "description": "A useful tool", "type": "Web app", "url": "https://example.com/tool"})
        self.assertEqual(project.status_code, 201)
        self.assertTrue(self.client.get("/api/creator/status").json["publishable"])

        public = self.client.get("/api/creators/maker")
        self.assertEqual(public.status_code, 200)
        self.assertNotIn("password_hash", public.text)
        self.assertEqual(self.client.get("/api/creators").json["total"], 1)

    def test_social_and_project_ownership(self):
        self.signup()
        self.create_profile()
        social_id = self.client.post("/api/creator/socials", json={"platform": "LinkedIn", "username": "maker", "profile_url": "https://linkedin.com/in/maker"}).json["social_account"]["id"]
        project_id = self.client.post("/api/creator/projects", json={"title": "Tool", "url": "https://example.com"}).json["project"]["id"]
        self.client.post("/api/auth/logout")
        self.signup("other@example.com")
        self.assertEqual(self.client.patch(f"/api/creator/socials/{social_id}", json={"username": "hacker"}).status_code, 404)
        self.assertEqual(self.client.patch(f"/api/creator/projects/{project_id}", json={"title": "Hacker"}).status_code, 404)

    def test_report_creation(self):
        self.signup()
        self.create_profile()
        creator_id = self.client.get("/api/creator/me").json["creator"]["id"]
        report = self.client.post("/api/reports", json={"creator_id": creator_id, "reason": "spam", "details": "Looks suspicious"})
        self.assertEqual(report.status_code, 201)
        self.assertEqual(self.client.post("/api/reports", json={"creator_id": 99999, "reason": "spam"}).status_code, 404)

    def test_protected_endpoints_require_login(self):
        self.assertEqual(self.client.get("/api/creator/me").status_code, 401)
        self.assertEqual(self.client.post("/api/creator", json={}).status_code, 401)
        self.assertEqual(self.client.post("/api/reports", json={}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
