import getpass
import os
from pathlib import Path

import django
import environ
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

BASE_DIR = Path(__file__).resolve().parent
env = environ.Env()
env.read_env(BASE_DIR / ".env")

if env.bool("IS_PREVIEW", default=False):
    raise SystemExit("Refusing to create a production admin while IS_PREVIEW is enabled.")

database_url = env.str("DATABASE_URL_DIRECT", default="")
if not database_url:
    raise SystemExit("DATABASE_URL_DIRECT must be configured in .env.")

os.environ["DATABASE_URL"] = database_url
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()

User = get_user_model()
email = "admin@pomsom.akili.com.ng"

existing_user = User.objects.filter(email=email).first()
if existing_user:
    if existing_user.is_superuser and existing_user.is_staff and existing_user.is_active:
        print(f"Admin account already exists: {email}")
        raise SystemExit(0)
    raise SystemExit(
        f"An account already uses {email}, but it is not an active superuser. "
        "Resolve the existing account manually before continuing."
    )

password = getpass.getpass("Set a strong admin password: ")
confirmation = getpass.getpass("Confirm admin password: ")
if not password or password != confirmation:
    raise SystemExit("Passwords were blank or did not match; no admin was created.")

admin = User(
    email=email,
    full_name="System Administrator",
    role=User.Role.ADMIN,
    is_active=True,
)
try:
    validate_password(password, user=admin)
except ValidationError as exc:
    raise SystemExit("Password rejected: " + "; ".join(exc.messages)) from exc

User.objects.create_superuser(
    email=email,
    password=password,
    full_name=admin.full_name,
    role=admin.role,
    is_active=True,
)
print(f"Admin account created: {email}")
