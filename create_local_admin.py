import os
import django

# Use dev settings for local SQLite
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create superuser if it doesn't exist
if not User.objects.filter(email='admin@pomsom.akili.com.ng').exists():
    user = User.objects.create_superuser(
        email='admin@pomsom.akili.com.ng',
        password='Admin@1234',
        full_name='System Administrator',
        role='ADMIN'
    )
    print(f"[OK] Superuser created locally: {user.email}")
    print(f"  Password: Admin@1234")
    print(f"  IMPORTANT: Change this password after first login!")
else:
    print("[OK] Superuser already exists locally: admin@pomsom.akili.com.ng")
