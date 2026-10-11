import unittest
import os
import json
from io import BytesIO
from unittest.mock import patch

import mysql.connector
from werkzeug.security import generate_password_hash

from app import PROJECTS, PROJECT_WORKFLOW, create_app


class FakeCursor:
    def __init__(self):
        self.statement = None
        self.parameters = None
        self.calls = []
        self.rows = []
        self.lastrowid = 42
        self.rowcount = 1
        self.closed = False

    def execute(self, statement, parameters=None):
        self.statement = statement
        self.parameters = parameters
        self.calls.append((statement, parameters))

    def close(self):
        self.closed = True

    def fetchone(self):
        return (1,)

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self):
        self.test_cursor = FakeCursor()
        self.committed = False
        self.closed = False

    def cursor(self, **_kwargs):
        return self.test_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def start_transaction(self):
        pass

    def is_connected(self):
        return not self.closed

    def close(self):
        self.closed = True


class PortfolioRoutesTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "WTF_CSRF_ENABLED": False,
                "OWNER_USERNAME": "john",
                "OWNER_PASSWORD_HASH": generate_password_hash("test-owner-password-123"),
            }
        )
        self.client = self.app.test_client()

    def dynamic_projects(self, published_only=True):
        projects = []
        for index, legacy in enumerate(PROJECTS, start=1):
            gallery = [
                {
                    "id": index * 100 + media_index,
                    "project_id": index,
                    "media_type": media["type"],
                    "file_name": media["file"],
                    "mime_type": "image/png",
                    "alt_text": media["alt"],
                    "url": f"/media/{index * 100 + media_index}",
                }
                for media_index, media in enumerate(legacy["gallery"], start=1)
            ]
            project = {
                **legacy,
                "id": index,
                "title": legacy["name"],
                "is_published": True,
                "workflow": PROJECT_WORKFLOW,
                "gallery": gallery,
                "cover_media_id": gallery[0]["id"],
                "cover_url": gallery[0]["url"],
            }
            projects.append(project)
        return projects if published_only else projects

    def test_database_project_loader_decodes_metadata_and_gallery(self):
        cursor = FakeCursor()
        cursor.fetchall = lambda: (
            [
                {
                    "id": 72,
                    "slug": "database-project",
                    "title": "Database Project",
                    "category": "Web design",
                    "description": "A project loaded from the portfolio database.",
                    "brief": "A clear project brief.",
                    "focus": "A focused visual system.",
                    "tools": '["Flask", "MySQL"]',
                    "workflow": json.dumps(PROJECT_WORKFLOW),
                    "is_published": 1,
                    "sort_order": 0,
                }
            ]
            if "FROM portfolio_media" not in cursor.statement
            else [
                {
                    "id": 901,
                    "project_id": 72,
                    "media_type": "image",
                    "file_name": "cover.png",
                    "mime_type": "image/png",
                    "alt_text": "Project cover",
                }
            ]
        )
        connection = FakeConnection()
        connection.test_cursor = cursor
        with self.app.test_request_context("/projects/database-project"):
            with patch("app.get_db_connection", return_value=connection):
                from app import load_projects

                projects = load_projects()
        self.assertEqual(projects[0]["tools"], ["Flask", "MySQL"])
        self.assertEqual(projects[0]["workflow"][0]["title"], "Listen & define")
        self.assertEqual(projects[0]["cover_media_id"], 901)
        self.assertEqual(projects[0]["gallery"][0]["url"], "/media/901")

    def test_public_pages_render(self):
        with patch("app.load_projects", side_effect=self.dynamic_projects):
            for path in ("/", "/about", "/projects", "/contact", "/projects/makkybites"):
                with self.subTest(path=path):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(b"John Garang", response.data)
                    self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
                    self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])

    def test_every_project_has_a_detailed_journey_page(self):
        with patch("app.load_projects", side_effect=self.dynamic_projects):
            for project in PROJECTS:
                with self.subTest(project=project["slug"]):
                    response = self.client.get(f"/projects/{project['slug']}")
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(project["name"].encode(), response.data)
                    self.assertIn(b"Listen &amp; define", response.data)
                    self.assertIn(b"Deliver &amp; hand over", response.data)
                    self.assertIn(b"Motion graphics opener", response.data)
                    self.assertIn(b"data-slide=\"0\"", response.data)
                    self.assertEqual(response.data.count(b'class="gallery-slide'), len(project["gallery"]) + 1)
                    first_slide = response.data.index(b'class="gallery-slide motion-slide is-active"')
                    first_media_slide = response.data.index(b'class="gallery-slide media-slide"')
                    self.assertLess(first_slide, first_media_slide)

    def test_project_gallery_assets_are_available(self):
        for project in PROJECTS:
            for media in project["gallery"]:
                with self.subTest(project=project["slug"], media=media["file"]):
                    response = self.client.get(
                        f"/static/files/assets/{'video' if media['type'] == 'video' else 'images'}/{media['file']}"
                    )
                    self.assertEqual(response.status_code, 200)
                    response.close()

    def test_unknown_project_returns_custom_not_found_page(self):
        with patch("app.load_projects", side_effect=self.dynamic_projects):
            response = self.client.get("/projects/unknown-project")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Project not found", response.data)

    def test_owner_pages_require_authentication(self):
        response = self.client.get("/owner/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/owner/login?next=/owner/")

    def test_owner_can_sign_in(self):
        response = self.client.post(
            "/owner/login",
            data={"username": "john", "password": "test-owner-password-123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/owner/")
        with patch("app.load_projects", return_value=[]):
            dashboard = self.client.get("/owner/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Your portfolio starts here", dashboard.data)

    def test_owner_project_form_renders_project_fields_and_default_journey(self):
        self.client.post(
            "/owner/login",
            data={"username": "john", "password": "test-owner-password-123"},
        )
        response = self.client.get("/owner/projects/new")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Project images and videos", response.data)
        self.assertIn(b"Listen &amp; define", response.data)
        self.assertIn(b"motion study automatically", response.data)

    def test_owner_project_upload_saves_project_and_binary_media(self):
        connection = FakeConnection()
        self.client.post(
            "/owner/login",
            data={"username": "john", "password": "test-owner-password-123"},
        )
        with patch("app.get_db_connection", return_value=connection):
            response = self.client.post(
                "/owner/projects/new",
                data={
                    "slug": "new-project",
                    "title": "New Project",
                    "category": "Web design",
                    "description": "A project description long enough to explain the work.",
                    "brief": "A project brief long enough to describe its starting point.",
                    "focus": "A focused visual and product direction.",
                    "tools": "Figma, Flask",
                    "workflow": json.dumps(PROJECT_WORKFLOW),
                    "is_published": "y",
                    "media_files": (BytesIO(b"\x89PNG\r\n\x1a\nportfolio-image"), "cover.png"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(connection.committed)
        self.assertIn("INSERT INTO portfolio", connection.test_cursor.calls[0][0])
        self.assertIn("INSERT INTO portfolio_media", connection.test_cursor.calls[1][0])
        self.assertEqual(connection.test_cursor.calls[1][1][5], b"\x89PNG\r\n\x1a\nportfolio-image")

    def test_invalid_upload_is_rejected_before_database_access(self):
        self.client.post(
            "/owner/login",
            data={"username": "john", "password": "test-owner-password-123"},
        )
        with patch("app.get_db_connection") as connect:
            response = self.client.post(
                "/owner/projects/new",
                data={
                    "slug": "new-project",
                    "title": "New Project",
                    "category": "Web design",
                    "description": "A project description long enough to explain the work.",
                    "brief": "A project brief long enough to describe its starting point.",
                    "focus": "A focused visual and product direction.",
                    "tools": "Figma",
                    "workflow": json.dumps(PROJECT_WORKFLOW),
                    "media_files": (BytesIO(b"not-an-image"), "cover.png"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 200)
        connect.assert_not_called()
        self.assertIn(b"file contents do not match", response.data)

    def test_portfolio_assets_are_served(self):
        for asset in (
            "favicon.svg",
            "files/styles/portfolio.css",
            "files/scripts/portfolio.js",
            "files/scripts/theme.js",
            "files/assets/IMG_20240825_011317.jpg",
            "files/assets/images/makkybites_homepage.png",
        ):
            with self.subTest(asset=asset):
                response = self.client.get(f"/static/{asset}")
                self.assertEqual(response.status_code, 200)
                response.close()

    def test_production_requires_secret_key(self):
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SECRET_KEY must be set"):
                create_app()

    def test_contact_form_requires_csrf_token(self):
        csrf_app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "WTF_CSRF_ENABLED": True,
            }
        )
        with self.assertLogs("flask_wtf.csrf", level="INFO"):
            response = csrf_app.test_client().post(
                "/contact",
                data={
                    "full_name": "John Example",
                    "email": "person@example.com",
                    "message": "I would like to discuss a website project.",
                },
            )
        self.assertEqual(response.status_code, 400)

    def test_contact_database_failure_returns_service_unavailable(self):
        with self.assertLogs("app", level="ERROR"):
            with patch(
                "app.mysql.connector.connect",
                side_effect=mysql.connector.Error("database unavailable"),
            ):
                response = self.client.post(
                    "/contact",
                    data={
                        "full_name": "John Example",
                        "email": "person@example.com",
                        "message": "I would like to discuss a website project.",
                    },
                )

        self.assertEqual(response.status_code, 503)
        self.assertIn(b"Your message could not be sent right now", response.data)

    def test_contact_submission_uses_parameterized_insert_and_commits(self):
        connection = FakeConnection()
        with patch("app.mysql.connector.connect", return_value=connection):
            response = self.client.post(
                "/contact",
                data={
                    "full_name": "  John Example ",
                    "email": " PERSON@EXAMPLE.COM ",
                    "phone": "",
                    "message": "I would like to discuss a website project.",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/contact")
        self.assertIn("INSERT INTO contact_messages", connection.test_cursor.statement)
        self.assertEqual(
            connection.test_cursor.parameters,
            (
                "John Example",
                "person@example.com",
                None,
                "I would like to discuss a website project.",
            ),
        )
        self.assertTrue(connection.committed)
        self.assertTrue(connection.test_cursor.closed)
        self.assertTrue(connection.closed)

    def test_invalid_contact_submission_is_not_saved(self):
        with patch("app.mysql.connector.connect") as connect:
            response = self.client.post(
                "/contact",
                data={
                    "full_name": "J",
                    "email": "not-an-email",
                    "message": "Short",
                },
            )

        self.assertEqual(response.status_code, 200)
        connect.assert_not_called()
        self.assertIn(b"Please correct the highlighted fields", response.data)


if __name__ == "__main__":
    unittest.main()
