import os
import sys
from pathlib import Path

# Add the project root to the path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')

# Import Django and setup
import django
django.setup()

# Import the WSGI application
from django.core.wsgi import get_wsgi_application

# This is the entrypoint for Vercel
application = get_wsgi_application()
