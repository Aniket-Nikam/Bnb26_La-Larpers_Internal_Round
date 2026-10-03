"""Create a new private local deployment configuration; never overwrite .env."""

import argparse
import base64
import os
import secrets
import subprocess
from pathlib import Path
from urllib.parse import urlparse

parser = argparse.ArgumentParser()
parser.add_argument("--demo", action="store_true")
parser.add_argument("--origin", help="Canonical public origin; normal profile requires HTTPS")
args = parser.parse_args()
origin = args.origin or ("http://localhost:8080" if args.demo else None)
if origin is None:
    parser.error("Normal deployments require --origin https://your-host")
parsed = urlparse(origin)
if (
    parsed.scheme not in ({"http", "https"} if args.demo else {"https"})
    or not parsed.netloc
    or parsed.path
    or parsed.query
    or parsed.fragment
    or parsed.username
    or parsed.password
):
    parser.error("Use a canonical origin with no path or credentials")
password = secrets.token_hex(24)
try:
    app_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
except (OSError, subprocess.CalledProcessError):
    app_commit = "unknown"
values = {
    "APP_PROFILE": "demo" if args.demo else "normal",
    "PUBLIC_ORIGIN": origin,
    "COOKIE_SECURE": "false" if args.demo else "true",
    "POSTGRES_DB": "fairdrop",
    "POSTGRES_USER": "fairdrop",
    "POSTGRES_PASSWORD": password,
    "DATABASE_URL": f"postgresql+psycopg://fairdrop:{password}@postgres:5432/fairdrop",
    "REDIS_URL": "redis://redis:6379/0",
    "SESSION_DIGEST_KEY": secrets.token_hex(32),
    "CREDENTIAL_DIGEST_KEY": secrets.token_hex(32),
    "SEED_ENCRYPTION_KEY": base64.b64encode(secrets.token_bytes(32)).decode(),
    "LAB_TARGET_ORIGIN": "http://gateway:8080",
    "APP_COMMIT": app_commit,
}
try:
    descriptor = os.open(Path(".env"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    parser.error(".env already exists; it was preserved")
with os.fdopen(descriptor, "w", encoding="utf-8") as out:
    out.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
print(
    "Created .env with random keys and the current commit. Refresh APP_COMMIT after code updates."
)
