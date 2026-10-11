import json
import logging
import sys
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parents[1]

from app import IMAGE_SIGNATURES, PROJECTS, PROJECT_WORKFLOW, app, get_db_connection


IMAGE_DIRECTORY = ROOT / "static" / "files" / "assets" / "images"


def image_record(filename):
    path = IMAGE_DIRECTORY / filename
    data = path.read_bytes()
    signature = IMAGE_SIGNATURES.get(path.suffix.lower())
    if signature is None or not signature[1](data[:16]):
        raise ValueError(f"Unsupported or invalid image file: {path}")
    return {
        "file_name": path.name,
        "mime_type": signature[0],
        "media_type": "image",
        "alt_text": path.stem[:255],
        "binary_data": data,
    }


def migrate():
    with app.app_context():
        connection = get_db_connection()
        cursor = connection.cursor()
        migrated_projects = 0
        migrated_media = 0
        try:
            connection.start_transaction()
            for order, project in enumerate(PROJECTS):
                cursor.execute("SELECT id FROM portfolio WHERE slug=%s", (project["slug"],))
                if cursor.fetchone():
                    continue
                cursor.execute(
                    """
                    INSERT INTO portfolio
                        (slug, title, category, description, brief, focus, tools, workflow,
                         is_published, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s)
                    """,
                    (
                        project["slug"],
                        project["name"],
                        project["category"],
                        project["description"],
                        project["brief"],
                        project["focus"],
                        json.dumps(project["tools"], ensure_ascii=False),
                        json.dumps(PROJECT_WORKFLOW, ensure_ascii=False),
                        order,
                    ),
                )
                project_id = cursor.lastrowid
                for media_order, item in enumerate(project["gallery"]):
                    media = image_record(item["file"])
                    media["alt_text"] = item["alt"][:255]
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
                            media_order,
                        ),
                    )
                    migrated_media += 1
                migrated_projects += 1

            portrait_path = ROOT / "static" / "files" / "assets" / "IMG_20240825_011317.jpg"
            portrait = portrait_path.read_bytes()
            signature = IMAGE_SIGNATURES[".jpg"]
            if not signature[1](portrait[:16]):
                raise ValueError(f"Unsupported or invalid image file: {portrait_path}")
            cursor.execute(
                """
                INSERT INTO portfolio_site_assets (asset_key, file_name, mime_type, binary_data)
                VALUES ('owner-portrait', %s, %s, %s)
                ON DUPLICATE KEY UPDATE file_name=VALUES(file_name),
                    mime_type=VALUES(mime_type), binary_data=VALUES(binary_data)
                """,
                (portrait_path.name, signature[0], portrait),
            )
            connection.commit()
        except Exception:
            try:
                connection.rollback()
            except mysql.connector.Error:
                logging.exception("Unable to roll back the portfolio migration transaction.")
            raise
        finally:
            cursor.close()
        print(f"Migrated {migrated_projects} new projects and {migrated_media} images.")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as error:
        print(f"Migration failed: {error}", file=sys.stderr)
        raise
