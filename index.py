import os
import sys
from pathlib import Path

# Add the project root to the path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')

# Import Django and setup
import django
django.setup()

# Import WSGI application
from config.wsgi import application

# Export the WSGI application for Vercel
app = application
