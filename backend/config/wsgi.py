"""
Punto de entrada WSGI para Gunicorn y servidores de producción.
Uso: gunicorn config.wsgi:application
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
