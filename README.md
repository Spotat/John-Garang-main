# John Garang Otieno Portfolio

A responsive portfolio website served by Flask. Projects, project journeys, gallery images/videos, and the portfolio owner's profile image are stored in MySQL. The contact form validates submissions on the server and stores them in MySQL.

The portfolio includes a persistent light/dark appearance preference (stored in local storage and a one-year site-wide cookie), responsive motion effects that respect reduced-motion settings, and a detail page for each project with a project-specific journey. Project details include an accessible, keyboard- and touch-navigable media carousel. Its animated SVG motion study is generated automatically from each project's title and category; image and video content is stored as binary media in MySQL. Display and body fonts use Syne and DM Sans from Google Fonts, with system-font fallbacks.

## Requirements

- Python 3.10+
- MySQL 8+

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies and create the local configuration file:

   ```powershell
   python -m pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

   Edit `.env` with MySQL/phpMyAdmin connection details, a long random `SECRET_KEY`, an owner username, and the hash generated below. `.env` is excluded from Git.

3. Create the schema in phpMyAdmin:

   - Open phpMyAdmin. If the `portfolio` database does not exist, use **New** to create it with `utf8mb4_unicode_ci`.
   - Select the `portfolio` database in the navigation panel, choose **Import**, select `db/schema.sql`, and run the import. It creates the `portfolio`, `portfolio_media`, `portfolio_site_assets`, and `contact_messages` tables.
   - Create a dedicated MySQL application account (do not use the phpMyAdmin/root account). Run this in phpMyAdmin's SQL tab, replacing the example password:

   ```sql
   CREATE USER 'portfolio'@'localhost' IDENTIFIED BY 'replace-with-a-long-database-password';
   GRANT SELECT, INSERT, UPDATE, DELETE ON portfolio.portfolio TO 'portfolio'@'localhost';
   GRANT SELECT, INSERT, UPDATE, DELETE ON portfolio.portfolio_media TO 'portfolio'@'localhost';
   GRANT SELECT, INSERT, UPDATE ON portfolio.portfolio_site_assets TO 'portfolio'@'localhost';
   GRANT INSERT ON portfolio.contact_messages TO 'portfolio'@'localhost';
   FLUSH PRIVILEGES;
   ```

   If the account already exists, use `ALTER USER` to change its password rather than re-running `CREATE USER`.

4. Configure the owner account. The username and password are entered locally; the password is not echoed, and only its hash is stored in ignored `.env`:

   ```powershell
   python scripts/hash_admin_password.py
   ```

   Set `MYSQL_PASSWORD` in `.env` to the MySQL application account password and replace the `SECRET_KEY` placeholder with a separate random secret.

   If the owner password is unavailable, run the same command again to replace the password hash. To have the local script generate a strong one-time password instead, run `python scripts/hash_admin_password.py --generate`, then sign in and keep the printed password in a password manager.

5. Copy the existing project descriptions and linked project/profile images into the database. The migration is transactional and safe to re-run; projects whose slugs already exist are left unchanged:

   ```powershell
   python -m scripts.migrate_portfolio
   ```

   The source image files remain in `static/files/assets/` as a recovery copy; active Flask portfolio pages load displayed project and profile media from the database. The stylesheet, scripts, icons, and fonts remain static web assets.

6. Start the local development server:

   ```powershell
   python app.py
   ```

   Open `http://127.0.0.1:5000`.

Public project pages require the schema and project migration to be applied. MySQL stores the contact submissions, project fields, per-project journey stages, uploaded media, and profile image. The owner workspace is available at `http://127.0.0.1:5000/owner/`; sign in with `OWNER_USERNAME` and the password used to create `OWNER_PASSWORD_HASH`.

## Managing projects

From the owner workspace, create, edit, publish/unpublish, or delete projects. Each project has a URL slug, category, public description, brief, creative focus, comma-separated tools, one or more project-journey stages, and an ordered media gallery. Upload JPG, PNG, GIF, or WebP images and MP4 or WebM video (up to 20 MB per file, 10 files and 50 MB total per save, with at least one image per project). The project detail page builds the motion study automatically; there is no separate motion file to upload. Unpublished projects and their media are visible only while the owner is signed in; private media responses are marked `no-store`.

## Production

- Set `APP_ENV=production`, `SECRET_KEY`, `MYSQL_*`, `OWNER_USERNAME`, and `OWNER_PASSWORD_HASH` in the hosting environment or secret manager. The app refuses to start in production without the secret key and owner credentials.
- Serve `wsgi:app` with a production WSGI server (for example, Gunicorn on Linux); do not expose Flask's development server.
- Terminate HTTPS at the web server or trusted proxy and set `COOKIE_SECURE=true` so session cookies are HTTPS-only and HSTS is enabled.
- Give the MySQL application user only the database/table privileges listed above and avoid using the MySQL root account.
- For a TLS-protected MySQL connection, set `MYSQL_SSL_CA` to the trusted server CA certificate. For mutual TLS, also set both `MYSQL_SSL_CERT` and `MYSQL_SSL_KEY`; the server certificate and hostname are verified when a CA is configured.
- Apply `db/schema.sql` as a deployment/migration step. The app intentionally does not create or alter production tables automatically.
- Configure backups, monitoring, and request rate limiting at the reverse proxy or hosting platform.

## Tests

Run the application tests with:

```powershell
python -m unittest discover -s tests
```
