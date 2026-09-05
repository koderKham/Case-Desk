import getpass
import hashlib
import hmac
import secrets
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "instance" / "case_manager.db"

def generate_password_hash(password, iterations=600_000):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"

def main():
    email = input("User email [admin@example.com]: ").strip().lower() or "admin@example.com"
    password = getpass.getpass("New password: ")
    confirm = getpass.getpass("Confirm password: ")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters.")
    if password != confirm:
        raise SystemExit("Passwords do not match.")

    db = sqlite3.connect(DB_PATH)
    cur = db.execute(
        "UPDATE users SET password_hash=? WHERE lower(email)=?",
        (generate_password_hash(password), email),
    )
    db.commit()
    db.close()

    if cur.rowcount == 0:
        raise SystemExit(f"No user found for {email}.")
    print(f"Password updated for {email}.")

if __name__ == "__main__":
    main()
