"""Настройка Django для тестов веб-слоя (pytest без pytest-django)."""

import os

import django
from django.test.utils import setup_test_environment

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "venue_service.settings")
django.setup()
setup_test_environment()
