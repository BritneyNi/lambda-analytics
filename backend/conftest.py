import pytest
from django.conf import settings


def pytest_configure(config):
    settings.configure(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "test_db",
                "USER": "postgres",
                "PASSWORD": "postgres",
                "HOST": "localhost",
                "PORT": "5432",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "rest_framework",
            "rest_framework_simplejwt",
            "django_filters",
            "dashboard",
        ],
        REST_FRAMEWORK={
            "DEFAULT_AUTHENTICATION_CLASSES": [
                "rest_framework_simplejwt.authentication.JWTAuthentication",
            ],
            "DEFAULT_PERMISSION_CLASSES": [
                "rest_framework.permissions.IsAuthenticated",
            ],
            "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
            "PAGE_SIZE": 10,
        },
        ROOT_URLCONF="config.urls",
        SECRET_KEY="test-secret-key",
        USE_TZ=True,
        TIME_ZONE="America/Bogota",
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        },
    )