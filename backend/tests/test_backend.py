import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app


class TestConfig:
    SECRET_KEY = "test-secret"
    DATABASE_PATH = Path(tempfile.gettempdir()) / "upnext-test.sqlite"
    FRONTEND_ORIGIN = "http://localhost:5173"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    EXPOSE_DB_INFO = False
    GITHUB_CLIENT_ID = "test-client-id"
    GITHUB_CLIENT_SECRET = "test-client-secret"
    GITHUB_OAUTH_CALLBACK_URL = "http://localhost:5000/api/creator/socials/github/callback"
    SPOTIFY_CLIENT_ID = "test-spotify-client-id"
    SPOTIFY_CLIENT_SECRET = "test-spotify-client-secret"
    SPOTIFY_OAUTH_CALLBACK_URL = "http://127.0.0.1:5000/api/creator/socials/spotify/callback"


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

    def github_social(self, username="maker"):
        return self.client.post("/api/creator/socials", json={"platform": "GitHub", "username": username, "profile_url": f"https://github.com/{username}"}).json["social_account"]

    def start_github_verification(self, social_id):
        response = self.client.get(f"/api/creator/socials/{social_id}/verify/github")
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            return session["github_oauth_state"]

    def test_github_verification_start_requires_ownership_and_github(self):
        self.assertEqual(self.client.get("/api/creator/socials/1/verify/github").status_code, 401)
        self.signup()
        self.create_profile()
        linkedin = self.client.post("/api/creator/socials", json={"platform": "LinkedIn", "username": "maker", "profile_url": "https://linkedin.com/in/maker"}).json["social_account"]
        self.assertEqual(self.client.get(f"/api/creator/socials/{linkedin['id']}/verify/github").status_code, 400)
        github = self.github_social()
        self.client.post("/api/auth/logout")
        self.signup("other@example.com")
        self.create_profile("other-maker")
        self.assertEqual(self.client.get(f"/api/creator/socials/{github['id']}/verify/github").status_code, 404)

    def test_github_oauth_state_and_successful_ownership_verification(self):
        self.signup()
        self.create_profile()
        social = self.github_social()
        state = self.start_github_verification(social["id"])
        with self.client.session_transaction() as session:
            self.assertEqual(session["github_oauth_social_id"], social["id"])
            self.assertTrue(session["github_oauth_state"])
        with patch("routes.socials.github_token_exchange", return_value="temporary-token"), patch("routes.socials.github_authenticated_user", return_value={"login": "MAKER", "id": 12345}):
            response = self.client.get(f"/api/creator/socials/github/callback?code=code&state={state}")
        self.assertIn("github_verification=success", response.location)
        updated = self.client.get("/api/creator/socials").json["social_accounts"][0]
        self.assertTrue(updated["ownership_verified"])
        self.assertEqual(updated["verification_status"], "verified")
        self.assertTrue(updated["verified_at"])
        self.assertNotIn("temporary-token", self.client.get("/api/creators/maker").text)
        with self.client.session_transaction() as session:
            self.assertNotIn("github_oauth_state", session)

    def test_github_callback_rejects_bad_state_denial_and_mismatch(self):
        self.signup()
        self.create_profile()
        social = self.github_social()
        state = self.start_github_verification(social["id"])
        bad = self.client.get("/api/creator/socials/github/callback?code=code&state=wrong")
        self.assertIn("github_verification=failed", bad.location)
        self.assertFalse(self.client.get("/api/creator/socials").json["social_accounts"][0]["ownership_verified"])
        state = self.start_github_verification(social["id"])
        denied = self.client.get(f"/api/creator/socials/github/callback?error=access_denied&state={state}")
        self.assertIn("github_verification=denied", denied.location)
        state = self.start_github_verification(social["id"])
        with patch("routes.socials.github_token_exchange", return_value="temporary-token"), patch("routes.socials.github_authenticated_user", return_value={"login": "another-user", "id": 9}):
            mismatch = self.client.get(f"/api/creator/socials/github/callback?code=code&state={state}")
        self.assertIn("github_verification=failed", mismatch.location)
        self.assertFalse(self.client.get("/api/creator/socials").json["social_accounts"][0]["ownership_verified"])

    def test_editing_verified_github_identity_invalidates_verification(self):
        self.signup()
        self.create_profile()
        social = self.github_social()
        state = self.start_github_verification(social["id"])
        with patch("routes.socials.github_token_exchange", return_value="temporary-token"), patch("routes.socials.github_authenticated_user", return_value={"login": "maker", "id": 12}):
            self.client.get(f"/api/creator/socials/github/callback?code=code&state={state}")
        updated = self.client.patch(f"/api/creator/socials/{social['id']}", json={"username": "other", "profile_url": "https://github.com/other"})
        self.assertEqual(updated.status_code, 200)
        self.assertFalse(updated.json["social_account"]["ownership_verified"])
        self.assertEqual(updated.json["social_account"]["verification_status"], "unverified")
        self.assertIsNone(updated.json["social_account"]["verified_at"])

    def spotify_social(self, user_id="maker"):
        return self.client.post("/api/creator/socials", json={"platform": "Spotify", "username": user_id, "profile_url": f"https://open.spotify.com/user/{user_id}"}).json["social_account"]

    def start_spotify_verification(self, social_id):
        response = self.client.get(f"/api/creator/socials/{social_id}/verify/spotify")
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            return session["spotify_oauth_state"]

    def test_spotify_verification_start_requires_ownership_and_spotify(self):
        self.assertEqual(self.client.get("/api/creator/socials/1/verify/spotify").status_code, 401)
        self.signup()
        self.create_profile()
        github = self.github_social()
        self.assertEqual(self.client.get(f"/api/creator/socials/{github['id']}/verify/spotify").status_code, 400)
        spotify = self.spotify_social()
        self.client.post("/api/auth/logout")
        self.signup("other@example.com")
        self.create_profile("other-maker")
        self.assertEqual(self.client.get(f"/api/creator/socials/{spotify['id']}/verify/spotify").status_code, 404)

    def test_spotify_oauth_state_success_and_immutable_account_id(self):
        self.signup()
        self.create_profile()
        social = self.spotify_social()
        state = self.start_spotify_verification(social["id"])
        with self.client.session_transaction() as session:
            self.assertEqual(session["spotify_oauth_social_id"], social["id"])
        with patch("routes.socials.spotify_token_exchange", return_value="spotify-access-token"), patch("routes.socials.spotify_authenticated_user", return_value={"id": "maker", "account_id": "immutable-account-id"}):
            response = self.client.get(f"/api/creator/socials/spotify/callback?code=code&state={state}")
        self.assertIn("spotify_verification=success", response.location)
        updated = self.client.get("/api/creator/socials").json["social_accounts"][0]
        self.assertTrue(updated["ownership_verified"])
        self.assertEqual(updated["verification_status"], "verified")
        self.assertNotIn("spotify-access-token", self.client.get("/api/creators/maker").text)
        connection = __import__("sqlite3").connect(self.db_path)
        self.assertEqual(connection.execute("SELECT provider_account_id FROM social_accounts WHERE id = ?", (social["id"],)).fetchone()[0], "immutable-account-id")
        self.assertEqual(connection.execute("SELECT count(*) FROM spotify_oauth_attempts").fetchone()[0], 0)
        connection.close()

    def test_spotify_callback_rejects_bad_state_denial_mismatch_and_token_failure(self):
        self.signup()
        self.create_profile()
        social = self.spotify_social()
        state = self.start_spotify_verification(social["id"])
        self.assertIn("spotify_verification=failed", self.client.get("/api/creator/socials/spotify/callback?code=code&state=wrong").location)
        state = self.start_spotify_verification(social["id"])
        self.assertIn("spotify_verification=denied", self.client.get(f"/api/creator/socials/spotify/callback?error=access_denied&state={state}").location)
        state = self.start_spotify_verification(social["id"])
        with patch("routes.socials.spotify_token_exchange", return_value=None):
            self.assertIn("spotify_verification=failed", self.client.get(f"/api/creator/socials/spotify/callback?code=code&state={state}").location)
        state = self.start_spotify_verification(social["id"])
        with patch("routes.socials.spotify_token_exchange", return_value="spotify-access-token"), patch("routes.socials.spotify_authenticated_user", return_value={"id": "other", "account_id": "other-account"}):
            self.assertIn("spotify_verification=failed", self.client.get(f"/api/creator/socials/spotify/callback?code=code&state={state}").location)
        self.assertFalse(self.client.get("/api/creator/socials").json["social_accounts"][0]["ownership_verified"])

    def test_editing_verified_spotify_identity_invalidates_verification(self):
        self.signup()
        self.create_profile()
        social = self.spotify_social()
        state = self.start_spotify_verification(social["id"])
        with patch("routes.socials.spotify_token_exchange", return_value="spotify-access-token"), patch("routes.socials.spotify_authenticated_user", return_value={"id": "maker", "account_id": "immutable-account-id"}):
            self.client.get(f"/api/creator/socials/spotify/callback?code=code&state={state}")
        updated = self.client.patch(f"/api/creator/socials/{social['id']}", json={"username": "other", "profile_url": "https://open.spotify.com/user/other"})
        self.assertEqual(updated.status_code, 200)
        self.assertFalse(updated.json["social_account"]["ownership_verified"])
        self.assertEqual(updated.json["social_account"]["verification_status"], "unverified")
        self.assertIsNone(updated.json["social_account"]["verified_at"])


if __name__ == "__main__":
    unittest.main()
