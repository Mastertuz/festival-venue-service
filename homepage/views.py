from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import escape


def page(title, content):
    """Собрать HTML-страницу: кодировка, заголовок, Bootstrap и навигация."""
    bootstrap = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3" "/dist/css/bootstrap.min.css"
    home_url = reverse("index")
    venues_url = reverse("venues")
    bookings_url = reverse("bookings")
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)}</title>
    <link rel="stylesheet" href="{bootstrap}">
</head>
<body>
    <nav class="nav border-bottom mb-4">
        <a class="nav-link" href="{home_url}">Главная</a>
        <a class="nav-link" href="{venues_url}">Площадки</a>
        <a class="nav-link" href="{bookings_url}">Бронирования</a>
    </nav>
    <main class="container">{content}</main>
</body>
</html>"""


def index(request):
    venues_url = reverse("venues")
    bookings_url = reverse("bookings")
    content = f"""
    <h1 class="display-4">Festival Venue Service</h1>
    <p class="lead">Сервис управления фестивальными площадками.</p>
    <p>Основные разделы:</p>
    <a href="{venues_url}" class="btn btn-primary me-2">Площадки</a>
    <a href="{bookings_url}" class="btn btn-secondary">Бронирования</a>
    """
    return HttpResponse(page("Festival Venue Service", content))
