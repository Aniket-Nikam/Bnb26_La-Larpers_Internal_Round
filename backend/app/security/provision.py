"""Offline provisioning. Prints the raw code once; redirect to a private file."""

import argparse
import secrets

from app.core.config import get_settings
from app.persistence.database import session_factory
from app.persistence.models import User
from app.security.provisioning import provision_credential, provision_user_with_credential


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--role", choices=["participant", "organizer", "admin"], default="participant"
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Explicitly provision a real account in normal profile",
    )
    args = parser.parse_args()
    if get_settings().app_profile == "normal" and not args.production:
        parser.error("Normal-profile provisioning requires --production")
    raw = secrets.token_urlsafe(32)
    with session_factory().begin() as db:
        if args.production:
            if not 1 <= len(args.name) <= 100:
                parser.error("Name must be 1..100 characters")
            user = User(display_name=args.name, role=args.role)
            db.add(user)
            db.flush()
            provision_credential(db, user.id, raw)
        else:
            user, _ = provision_user_with_credential(db, args.name, args.role, raw)
        public_id = user.public_id
    print(f"public_id={public_id}\naccess_code={raw}")


if __name__ == "__main__":
    main()
