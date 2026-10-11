import logging
import os
import hmac
import json
import re
from datetime import date
from functools import wraps
from io import BytesIO
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, abort, flash, g, redirect, render_template, request, send_file, session, url_for
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from wtforms import BooleanField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp


csrf = CSRFProtect()
load_dotenv()

PROJECTS = [
    {
        "slug": "makkybites",
        "name": "MakkyBites",
        "category": "Web design & development",
        "image": "makkybites_homepage.png",
        "description": "A vibrant food brand experience combining clear product presentation with custom visual identity.",
        "brief": "Bring a food brand's products and personality together in a clear, welcoming digital experience.",
        "focus": "A lively visual direction, direct product presentation, and an experience that feels easy to browse.",
        "gallery": [
            {"type": "image", "file": "makkybites_homepage.png", "alt": "MakkyBites homepage design"},
            {"type": "image", "file": "makkybites_Intro_post.png", "alt": "MakkyBites brand introduction"},
        ],
        "tools": ["HTML", "CSS", "JavaScript", "Flask", "SQL"],
    },
    {
        "slug": "stealthpro-solutions",
        "name": "StealthPro Solutions",
        "category": "Web development",
        "image": "Stealth_Pro_Mockup.png",
        "description": "A polished digital presence for a security-focused brand, shaped around a confident visual system.",
        "brief": "Give a security-focused business a confident and considered online presence.",
        "focus": "A focused layout and strong visual hierarchy that keep the brand message clear.",
        "gallery": [
            {"type": "image", "file": "Stealth_Pro_Mockup.png", "alt": "StealthPro Solutions website mockup"},
            {"type": "image", "file": "StealthPro_Intro_post3.png", "alt": "StealthPro Solutions visual identity"},
        ],
        "tools": ["HTML", "CSS", "JavaScript", "Figma"],
    },
    {
        "slug": "chsupport",
        "name": "CHSupport",
        "category": "Charity website",
        "image": "chsupport_flyer_deck.png",
        "description": "A community-minded charity project with an approachable brand and accessible web experience.",
        "brief": "Make a community organisation's purpose and support easier for visitors to understand.",
        "focus": "An approachable tone, clear content structure, and accessible design choices.",
        "gallery": [
            {"type": "image", "file": "chsupport_flyer_deck.png", "alt": "CHSupport campaign design"},
            {"type": "image", "file": "NG_CDF_admin_portal_tab=support2.png", "alt": "Community support portal interface"},
        ],
        "tools": ["HTML", "CSS", "JavaScript", "Python", "SQL"],
    },
    {
        "slug": "tillwise",
        "name": "Tillwise",
        "category": "Brand identity",
        "image": "farm_design_deck.png",
        "description": "A distinctive visual identity designed to bring clarity and consistency to a growing brand.",
        "brief": "Establish a recognisable identity that can be carried consistently across brand touchpoints.",
        "focus": "A considered visual direction and a flexible identity system.",
        "gallery": [
            {"type": "image", "file": "farm_design_deck.png", "alt": "Tillwise brand design presentation"},
        ],
        "tools": ["Figma", "Photoshop", "Adobe Express"],
    },
    {
        "slug": "amani-africa",
        "name": "AMANI Africa",
        "category": "Brand identity",
        "image": "CHSupport B.Card.png",
        "description": "A memorable brand direction expressed through carefully considered print and digital assets.",
        "brief": "Shape a memorable brand presence and express it across print and digital applications.",
        "focus": "A cohesive visual language that can adapt to different formats.",
        "gallery": [
            {"type": "image", "file": "CHSupport B.Card.png", "alt": "AMANI Africa brand collateral"},
        ],
        "tools": ["Figma", "Photoshop", "Adobe Express"],
    },
    {
        "slug": "swim-fit",
        "name": "Swim Fit",
        "category": "Web design",
        "image": "swim_design.png",
        "description": "A clean, energetic web concept built to make a fitness brand feel welcoming and easy to explore.",
        "brief": "Create an energetic web direction that makes a fitness brand feel inviting and easy to navigate.",
        "focus": "A clean page structure, responsive layouts, and a visual language with movement.",
        "gallery": [
            {"type": "image", "file": "swim_design.png", "alt": "Swim Fit web design"},
        ],
        "tools": ["HTML", "CSS", "JavaScript"],
    },
    {
        "slug": "natco-inc",
        "name": "NATCO Inc",
        "category": "Dashboard development",
        "image": "dash.jpg",
        "description": "A dashboard project focused on presenting operational information in a clear, usable interface.",
        "brief": "Organise operational information into a dashboard that feels clear and manageable.",
        "focus": "Readable information hierarchy, useful interface patterns, and a considered data layout.",
        "gallery": [
            {"type": "image", "file": "dash.jpg", "alt": "NATCO Inc dashboard preview"},
        ],
        "tools": ["FastAPI", "HTML", "CSS", "JavaScript", "SQL"],
    },
]

PROJECT_WORKFLOW = [
    {
        "title": "Listen & define",
        "description": "Start with the brief: understand the audience, the purpose, and the practical constraints. Agree what a useful result should make easier.",
        "deliverable": "Shared goals and scope",
    },
    {
        "title": "Explore the direction",
        "description": "Review the content and context, then map the key experience. Explore visual directions and structure before committing to the details.",
        "deliverable": "A clear design direction",
    },
    {
        "title": "Design & build",
        "description": "Turn the agreed direction into a working experience. Develop the interface in responsive pieces and keep implementation aligned with the design.",
        "deliverable": "A working, responsive experience",
    },
    {
        "title": "Test & refine",
        "description": "Check the experience across screen sizes, review the content and interactions, and refine the details that affect usability and consistency.",
        "deliverable": "A reviewed final version",
    },
    {
        "title": "Deliver & hand over",
        "description": "Prepare the finished work for its next step, share the relevant files or deployment hand-off, and leave the work organised for ongoing use.",
        "deliverable": "A considered project hand-off",
    },
]


def strip_form_value(value):
    return value.strip() if isinstance(value, str) else value


class ContactForm(FlaskForm):
    full_name = StringField(
        "Full name",
        filters=[strip_form_value],
        validators=[DataRequired(), Length(min=2, max=120)],
    )
    email = StringField(
        "Email address",
        filters=[strip_form_value],
        validators=[DataRequired(), Email(), Length(max=254)],
    )
    phone = StringField(
        "Phone number (optional)",
        filters=[strip_form_value],
        validators=[Optional(), Length(max=32)],
    )
    message = TextAreaField(
        "How can I help?",
        filters=[strip_form_value],
        validators=[DataRequired(), Length(min=10, max=5000)],
    )
    submit = SubmitField("Send message")


class OwnerLoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=256)])
    submit = SubmitField("Sign in")


class ProjectForm(FlaskForm):
    slug = StringField(
        "URL slug",
        filters=[strip_form_value],
        validators=[
            DataRequired(),
            Length(max=120),
            Regexp(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", message="Use lowercase letters, numbers, and hyphens."),
        ],
    )
    title = StringField("Project name", filters=[strip_form_value], validators=[DataRequired(), Length(max=160)])
    category = StringField("Category", filters=[strip_form_value], validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Short description", filters=[strip_form_value], validators=[DataRequired(), Length(max=2000)])
    brief = TextAreaField("Project brief", filters=[strip_form_value], validators=[DataRequired(), Length(max=5000)])
    focus = TextAreaField("Creative focus", filters=[strip_form_value], validators=[DataRequired(), Length(max=2000)])
    tools = StringField("Tools (comma-separated)", filters=[strip_form_value], validators=[DataRequired(), Length(max=1000)])
    workflow = TextAreaField("Project journey (JSON)", validators=[DataRequired(), Length(max=20000)])
    is_published = BooleanField("Publish this project")
    submit = SubmitField("Save project")


IMAGE_SIGNATURES = {
    ".jpg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ".png": ("image/png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    ".gif": ("image/gif", lambda data: data.startswith((b"GIF87a", b"GIF89a"))),
    ".webp": ("image/webp", lambda data: data.startswith(b"RIFF") and data[8:12] == b"WEBP"),
}
VIDEO_SIGNATURES = {
    ".mp4": ("video/mp4", lambda data: len(data) >= 12 and data[4:8] == b"ftyp"),
    ".webm": ("video/webm", lambda data: data.startswith(b"\x1a\x45\xdf\xa3")),
}
MAX_MEDIA_FILE_SIZE = 20 * 1024 * 1024
MAX_MEDIA_FILES = 10


def load_projects(published_only=True):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = (
            "SELECT id, slug, title, category, description, brief, focus, tools, workflow, "
            "is_published, sort_order FROM portfolio"
        )
        if published_only:
            query += " WHERE is_published = TRUE"
        query += " ORDER BY sort_order, id"
        cursor.execute(query)
        rows = cursor.fetchall()
        if not rows:
            return []

        project_ids = [row["id"] for row in rows]
        placeholders = ", ".join(["%s"] * len(project_ids))
        cursor.execute(
            "SELECT id, project_id, media_type, file_name, mime_type, alt_text "
            f"FROM portfolio_media WHERE project_id IN ({placeholders}) ORDER BY sort_order, id",
            tuple(project_ids),
        )
        media_by_project = {project_id: [] for project_id in project_ids}
        for media in cursor.fetchall():
            media["url"] = url_for("portfolio_media", media_id=media["id"])
            media_by_project[media["project_id"]].append(media)

        projects = []
        for row in rows:
            tools = row["tools"]
            workflow = row["workflow"]
            if isinstance(tools, str):
                tools = json.loads(tools)
            if isinstance(workflow, str):
                workflow = json.loads(workflow)
            gallery = media_by_project[row["id"]]
            cover = next((media for media in gallery if media["media_type"] == "image"), None)
            projects.append(
                {
                    **row,
                    "name": row["title"],
                    "tools": tools,
                    "workflow": workflow,
                    "gallery": gallery,
                    "cover_media_id": cover["id"] if cover else None,
                    "cover_url": cover["url"] if cover else None,
                }
            )
        return projects
    finally:
        cursor.close()


def owner_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("owner_authenticated"):
            return redirect(url_for("owner_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def validate_workflow_json(value):
    try:
        workflow = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError("Project journey must be valid JSON.") from error
    if not isinstance(workflow, list) or not 1 <= len(workflow) <= 10:
        raise ValueError("Add between 1 and 10 journey stages.")
    for step in workflow:
        if not isinstance(step, dict) or not all(
            isinstance(step.get(field), str) and step[field].strip()
            for field in ("title", "description", "deliverable")
        ):
            raise ValueError("Each journey stage needs a title, description, and milestone.")
        if any(len(step[field]) > maximum for field, maximum in (
            ("title", 160), ("description", 2000), ("deliverable", 255)
        )):
            raise ValueError("Journey stage text exceeds the allowed length.")
    return workflow


def parse_tools(value):
    tools = [tool.strip() for tool in value.split(",") if tool.strip()]
    if not tools or len(tools) > 40 or any(len(tool) > 60 for tool in tools):
        raise ValueError("Add between 1 and 40 tools, each no longer than 60 characters.")
    return tools


def read_uploaded_media(upload):
    filename = secure_filename(upload.filename or "")
    extension = Path(filename).suffix.lower()
    signature = IMAGE_SIGNATURES.get(extension) or VIDEO_SIGNATURES.get(extension)
    if not filename or signature is None:
        raise ValueError("Choose a JPG, PNG, GIF, WebP, MP4, or WebM file.")
    data = upload.stream.read(MAX_MEDIA_FILE_SIZE + 1)
    if not data or len(data) > MAX_MEDIA_FILE_SIZE:
        raise ValueError("Each media file must be between 1 byte and 20 MB.")
    mime_type, matches_signature = signature
    if not matches_signature(data[:16]):
        raise ValueError(f"The file contents do not match {filename}'s extension.")
    media_type = "video" if extension in VIDEO_SIGNATURES else "image"
    return {
        "file_name": filename[:255],
        "mime_type": mime_type,
        "media_type": media_type,
        "alt_text": Path(filename).stem[:255],
        "binary_data": data,
    }


def insert_media(cursor, project_id, media, sort_order):
    cursor.execute(
        """
        INSERT INTO portfolio_media
            (project_id, media_type, file_name, mime_type, alt_text, binary_data, sort_order)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            project_id,
            media["media_type"],
            media["file_name"],
            media["mime_type"],
            media["alt_text"],
            media["binary_data"],
            sort_order,
        ),
    )


def get_db_connection():
    if "db_connection" not in g:
        connection_options = {
            "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
            "port": int(os.environ.get("MYSQL_PORT", "3306")),
            "user": os.environ.get("MYSQL_USER", "portfolio"),
            "password": os.environ.get("MYSQL_PASSWORD", ""),
            "database": os.environ.get("MYSQL_DATABASE", "portfolio"),
            "charset": "utf8mb4",
            "connection_timeout": 5,
        }
        ssl_ca = os.environ.get("MYSQL_SSL_CA")
        ssl_cert = os.environ.get("MYSQL_SSL_CERT")
        ssl_key = os.environ.get("MYSQL_SSL_KEY")
        if bool(ssl_cert) != bool(ssl_key):
            raise RuntimeError("MYSQL_SSL_CERT and MYSQL_SSL_KEY must be configured together.")
        if ssl_cert and not ssl_ca:
            raise RuntimeError("MYSQL_SSL_CA is required when using a MySQL client certificate.")
        if ssl_ca:
            connection_options.update(
                ssl_ca=ssl_ca,
                ssl_verify_cert=True,
                ssl_verify_identity=True,
            )
        if ssl_cert:
            connection_options.update(ssl_cert=ssl_cert, ssl_key=ssl_key)
        g.db_connection = mysql.connector.connect(**connection_options)
    return g.db_connection


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or os.urandom(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "").lower() == "true",
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
        WTF_CSRF_TIME_LIMIT=3600,
        OWNER_USERNAME=os.environ.get("OWNER_USERNAME", ""),
        OWNER_PASSWORD_HASH=os.environ.get("OWNER_PASSWORD_HASH", ""),
    )
    if test_config:
        app.config.update(test_config)

    if os.environ.get("FLASK_DEBUG", "").lower() != "true":
        logging.basicConfig(level=logging.INFO)
    if os.environ.get("APP_ENV", "").lower() == "production":
        if not os.environ.get("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY must be set in production.")
        if not app.config["OWNER_USERNAME"] or not app.config["OWNER_PASSWORD_HASH"]:
            raise RuntimeError("OWNER_USERNAME and OWNER_PASSWORD_HASH must be set in production.")
        if not app.config["SESSION_COOKIE_SECURE"]:
            app.logger.warning("COOKIE_SECURE should be true when HTTPS is enabled.")

    @app.before_request
    def set_request_size_limit():
        if request.endpoint in {"owner_project_new", "owner_project_edit"}:
            request.max_content_length = 50 * 1024 * 1024
        else:
            request.max_content_length = 64 * 1024

    csrf.init_app(app)

    @app.context_processor
    def inject_current_year():
        return {"current_year": date.today().year}

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' https://fonts.googleapis.com; "
            "script-src 'self'; font-src 'self' https://fonts.gstatic.com; form-action 'self'; "
            "base-uri 'self'; frame-ancestors 'none'",
        )
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response

    @app.teardown_appcontext
    def close_db_connection(_exception=None):
        connection = g.pop("db_connection", None)
        if connection is not None and connection.is_connected():
            connection.close()

    @app.get("/")
    def home():
        try:
            return render_template("home.html", projects=load_projects()[:3])
        except mysql.connector.Error:
            app.logger.exception("Unable to load public projects.")
            return render_template("error.html", title="Project catalogue unavailable", code=503), 503

    @app.get("/about")
    def about():
        return render_template("about.html")

    @app.get("/projects")
    def projects():
        try:
            return render_template("projects.html", projects=load_projects())
        except mysql.connector.Error:
            app.logger.exception("Unable to load public projects.")
            return render_template("error.html", title="Project catalogue unavailable", code=503), 503

    @app.get("/projects/<slug>")
    def project_detail(slug):
        try:
            all_projects = load_projects()
        except mysql.connector.Error:
            app.logger.exception("Unable to load project detail.")
            return render_template("error.html", title="Project catalogue unavailable", code=503), 503
        project = next((item for item in all_projects if item["slug"] == slug), None)
        if project is None:
            return render_template("error.html", title="Project not found", code=404), 404
        return render_template(
            "project_detail.html",
            project=project,
            workflow=project["workflow"],
            related_projects=[item for item in all_projects if item["slug"] != slug][:2],
        )

    @app.get("/media/<int:media_id>")
    def portfolio_media(media_id):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT m.file_name, m.mime_type, m.binary_data, p.is_published
                FROM portfolio_media m
                JOIN portfolio p ON p.id = m.project_id
                WHERE m.id = %s
                """,
                (media_id,),
            )
            media = cursor.fetchone()
        finally:
            cursor.close()
        if media is None or (not media["is_published"] and not session.get("owner_authenticated")):
            abort(404)
        response = send_file(
            BytesIO(media["binary_data"]),
            mimetype=media["mime_type"],
            download_name=secure_filename(media["file_name"]),
            conditional=True,
            max_age=86400 if media["is_published"] else None,
        )
        if not media["is_published"]:
            response.cache_control.private = True
            response.cache_control.no_store = True
        return response

    @app.get("/site-assets/<asset_key>")
    def portfolio_site_asset(asset_key):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT file_name, mime_type, binary_data FROM portfolio_site_assets WHERE asset_key = %s",
                (asset_key,),
            )
            asset = cursor.fetchone()
        finally:
            cursor.close()
        if asset is None:
            abort(404)
        return send_file(
            BytesIO(asset["binary_data"]),
            mimetype=asset["mime_type"],
            download_name=secure_filename(asset["file_name"]),
            conditional=True,
            max_age=86400,
        )

    @app.route("/owner/login", methods=["GET", "POST"])
    def owner_login():
        if session.get("owner_authenticated"):
            return redirect(url_for("owner_dashboard"))
        if not app.config["OWNER_USERNAME"] or not app.config["OWNER_PASSWORD_HASH"]:
            return render_template("error.html", title="Owner login is not configured", code=503), 503
        form = OwnerLoginForm()
        if form.validate_on_submit():
            try:
                valid_password = check_password_hash(
                    app.config["OWNER_PASSWORD_HASH"], form.password.data
                )
            except ValueError:
                app.logger.exception("OWNER_PASSWORD_HASH is invalid.")
                return render_template("error.html", title="Owner login is misconfigured", code=503), 503
            if hmac.compare_digest(form.username.data, app.config["OWNER_USERNAME"]) and valid_password:
                session.clear()
                session["owner_authenticated"] = True
                flash("Welcome back.", "success")
                return redirect(url_for("owner_dashboard"))
            flash("The username or password was not recognised.", "error")
        return render_template("owner_login.html", form=form)

    @app.post("/owner/logout")
    @owner_required
    def owner_logout():
        session.clear()
        flash("You have signed out.", "success")
        return redirect(url_for("owner_login"))

    @app.get("/owner/")
    @owner_required
    def owner_dashboard():
        try:
            return render_template("owner_dashboard.html", projects=load_projects(published_only=False))
        except mysql.connector.Error:
            app.logger.exception("Unable to load owner dashboard.")
            return render_template("error.html", title="Owner dashboard unavailable", code=503), 503

    @app.route("/owner/projects/new", methods=["GET", "POST"])
    @owner_required
    def owner_project_new():
        form = ProjectForm()
        if request.method == "GET":
            form.workflow.data = json.dumps(PROJECT_WORKFLOW, ensure_ascii=False, indent=2)
            form.is_published.data = True
        if form.validate_on_submit():
            try:
                workflow = validate_workflow_json(form.workflow.data)
                tools = parse_tools(form.tools.data)
                uploads = [upload for upload in request.files.getlist("media_files") if upload.filename]
                if len(uploads) > MAX_MEDIA_FILES:
                    raise ValueError(f"Upload no more than {MAX_MEDIA_FILES} files at once.")
                media_items = [read_uploaded_media(upload) for upload in uploads]
                if not any(media["media_type"] == "image" for media in media_items):
                    raise ValueError("Upload at least one project image.")
            except ValueError as error:
                flash(str(error), "error")
                return render_template("owner_project_form.html", form=form, project=None)

            connection = get_db_connection()
            cursor = connection.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO portfolio
                        (slug, title, category, description, brief, focus, tools, workflow, is_published)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        form.slug.data,
                        form.title.data,
                        form.category.data,
                        form.description.data,
                        form.brief.data,
                        form.focus.data,
                        json.dumps(tools),
                        json.dumps(workflow, ensure_ascii=False),
                        form.is_published.data,
                    ),
                )
                project_id = cursor.lastrowid
                for position, media in enumerate(media_items):
                    insert_media(cursor, project_id, media, position)
                connection.commit()
            except mysql.connector.IntegrityError:
                connection.rollback()
                flash("That URL slug is already in use. Choose a different one.", "error")
                return render_template("owner_project_form.html", form=form, project=None)
            except mysql.connector.Error:
                connection.rollback()
                raise
            finally:
                cursor.close()
            flash("Project created.", "success")
            return redirect(url_for("owner_dashboard"))
        return render_template("owner_project_form.html", form=form, project=None)

    @app.route("/owner/projects/<int:project_id>/edit", methods=["GET", "POST"])
    @owner_required
    def owner_project_edit(project_id):
        try:
            project = next(
                (item for item in load_projects(published_only=False) if item["id"] == project_id),
                None,
            )
        except mysql.connector.Error:
            app.logger.exception("Unable to load project for editing.")
            return render_template("error.html", title="Project editor unavailable", code=503), 503
        if project is None:
            abort(404)
        form = ProjectForm()
        if request.method == "GET":
            form.slug.data = project["slug"]
            form.title.data = project["title"]
            form.category.data = project["category"]
            form.description.data = project["description"]
            form.brief.data = project["brief"]
            form.focus.data = project["focus"]
            form.tools.data = ", ".join(project["tools"])
            form.workflow.data = json.dumps(project["workflow"], ensure_ascii=False, indent=2)
            form.is_published.data = bool(project["is_published"])
        if form.validate_on_submit():
            try:
                workflow = validate_workflow_json(form.workflow.data)
                tools = parse_tools(form.tools.data)
                uploads = [upload for upload in request.files.getlist("media_files") if upload.filename]
                remove_ids = request.form.getlist("remove_media")
                if len(uploads) > MAX_MEDIA_FILES:
                    raise ValueError(f"Upload no more than {MAX_MEDIA_FILES} files at once.")
                media_items = [read_uploaded_media(upload) for upload in uploads]
            except ValueError as error:
                flash(str(error), "error")
                return render_template("owner_project_form.html", form=form, project=project)

            connection = get_db_connection()
            cursor = connection.cursor()
            try:
                cursor.execute(
                    """
                    UPDATE portfolio SET slug=%s, title=%s, category=%s, description=%s,
                        brief=%s, focus=%s, tools=%s, workflow=%s, is_published=%s
                    WHERE id=%s
                    """,
                    (
                        form.slug.data,
                        form.title.data,
                        form.category.data,
                        form.description.data,
                        form.brief.data,
                        form.focus.data,
                        json.dumps(tools),
                        json.dumps(workflow, ensure_ascii=False),
                        form.is_published.data,
                        project_id,
                    ),
                )
                if remove_ids:
                    placeholders = ", ".join(["%s"] * len(remove_ids))
                    cursor.execute(
                        f"DELETE FROM portfolio_media WHERE project_id=%s AND id IN ({placeholders})",
                        (project_id, *remove_ids),
                    )
                cursor.execute(
                    "SELECT COUNT(*) FROM portfolio_media WHERE project_id=%s AND media_type='image'",
                    (project_id,),
                )
                image_count = cursor.fetchone()[0]
                image_count += sum(media["media_type"] == "image" for media in media_items)
                if image_count < 1:
                    connection.rollback()
                    flash("Keep or upload at least one project image.", "error")
                    return render_template("owner_project_form.html", form=form, project=project)
                cursor.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM portfolio_media WHERE project_id=%s",
                    (project_id,),
                )
                position = cursor.fetchone()[0]
                for media in media_items:
                    insert_media(cursor, project_id, media, position)
                    position += 1
                connection.commit()
            except mysql.connector.IntegrityError:
                connection.rollback()
                flash("That URL slug is already in use. Choose a different one.", "error")
                return render_template("owner_project_form.html", form=form, project=project)
            except mysql.connector.Error:
                connection.rollback()
                raise
            finally:
                cursor.close()
            flash("Project updated.", "success")
            return redirect(url_for("owner_dashboard"))
        return render_template("owner_project_form.html", form=form, project=project)

    @app.post("/owner/projects/<int:project_id>/delete")
    @owner_required
    def owner_project_delete(project_id):
        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("DELETE FROM portfolio WHERE id=%s", (project_id,))
            if cursor.rowcount == 0:
                connection.rollback()
                abort(404)
            connection.commit()
        except mysql.connector.Error:
            connection.rollback()
            raise
        finally:
            cursor.close()
        flash("Project and its stored media have been deleted.", "success")
        return redirect(url_for("owner_dashboard"))

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        form = ContactForm()
        if form.validate_on_submit():
            try:
                connection = get_db_connection()
                cursor = connection.cursor()
                try:
                    cursor.execute(
                        """
                        INSERT INTO contact_messages (full_name, email, phone, message)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            form.full_name.data.strip(),
                            form.email.data.strip().lower(),
                            form.phone.data.strip() if form.phone.data else None,
                            form.message.data.strip(),
                        ),
                    )
                    connection.commit()
                finally:
                    cursor.close()
                flash("Thanks for reaching out. Your message has been sent.", "success")
                return redirect(url_for("contact"))
            except mysql.connector.Error:
                app.logger.exception("Unable to save contact form submission.")
                flash(
                    "Your message could not be sent right now. Please try again later "
                    "or email hello@johngarangotieno.com.",
                    "error",
                )
                return render_template("contact.html", form=form), 503
        return render_template("contact.html", form=form)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", title="Page not found", code=404), 404

    @app.errorhandler(413)
    def request_too_large(_error):
        return render_template("error.html", title="Request too large", code=413), 413

    @app.errorhandler(mysql.connector.Error)
    def database_error(_error):
        app.logger.exception("An unhandled MySQL operation failed.")
        return render_template("error.html", title="Portfolio database unavailable", code=503), 503

    @app.errorhandler(500)
    def internal_server_error(_error):
        return render_template("error.html", title="Something went wrong", code=500), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run()
