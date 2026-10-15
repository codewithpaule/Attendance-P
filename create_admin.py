import os
import django

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
    print(f"[OK] Superuser created: {user.email}")
    print(f"  Password: Admin@1234")
else:
    print("[OK] Superuser already exists: admin@pomsom.akili.com.ng")
