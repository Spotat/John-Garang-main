import argparse
import re
import secrets
from getpass import getpass
from pathlib import Path

from werkzeug.security import generate_password_hash


def main():
    parser = argparse.ArgumentParser(description="Configure the portfolio owner login in .env.")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="generate a strong one-time password and print it once",
    )
    parser.add_argument("--username", help="owner username to save")
    args = parser.parse_args()
    env_file = Path(".env")
    if not env_file.is_file():
        raise SystemExit("Create .env from .env.example before configuring owner login.")

    lines = env_file.read_text(encoding="utf-8").splitlines()
    configured_username = next(
        (
            match.group(1).strip()
            for line in lines
            if (match := re.match(r"^\s*OWNER_USERNAME\s*=(.*)$", line))
        ),
        "john",
    )
    if args.username:
        username = args.username.strip()
    elif args.generate:
        username = configured_username
    else:
        username = input(f"Owner username [{configured_username}]: ").strip() or configured_username
    if not re.fullmatch(r"[A-Za-z0-9_.@-]{1,80}", username):
        raise SystemExit("Use 1-80 letters, numbers, dots, underscores, @, or hyphens for the username.")
    if args.generate:
        password = secrets.token_urlsafe(32)
    else:
        password = getpass("Choose an owner-dashboard password (minimum 14 characters): ")
        if len(password) < 14:
            raise SystemExit("Use at least 14 characters.")
        confirmation = getpass("Repeat the password: ")
        if password != confirmation:
            raise SystemExit("The passwords do not match.")

    entries = {
        "OWNER_USERNAME": username,
        "OWNER_PASSWORD_HASH": generate_password_hash(password),
    }
    found = set()
    updated_lines = []
    for line in lines:
        match = re.match(r"^\s*(OWNER_USERNAME|OWNER_PASSWORD_HASH)\s*=", line)
        if match:
            key = match.group(1)
            updated_lines.append(f"{key}={entries[key]}")
            found.add(key)
        else:
            updated_lines.append(line)
    for key, value in entries.items():
        if key not in found:
            updated_lines.append(f"{key}={value}")
    env_file.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    print(f"Owner login configured in {env_file}. Restart Flask to apply the change.")
    if args.generate:
        print(f"Username: {username}")
        print(f"Temporary password: {password}")
        print("Save it now; only the hash is stored in .env.")
    else:
        print("The password hash is stored in .env; the password was not written to disk.")


if __name__ == "__main__":
    main()
