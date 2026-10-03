import base64
import os
import secrets

os.environ.setdefault("APP_PROFILE", "test")
os.environ.setdefault("SESSION_DIGEST_KEY", secrets.token_hex(32))
os.environ.setdefault("CREDENTIAL_DIGEST_KEY", secrets.token_hex(32))
os.environ.setdefault("SEED_ENCRYPTION_KEY", base64.b64encode(secrets.token_bytes(32)).decode())
os.environ.setdefault("PUBLIC_ORIGIN", "http://testclient")
os.environ.setdefault("COOKIE_SECURE", "false")
