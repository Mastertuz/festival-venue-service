from django.shortcuts import render
from django.urls import reverse
from django.utils.html import escape


def page(title, content):
    """Собрать HTML-страницу: кодировка, заголовок, Bootstrap и навигация."""
    bootstrap = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3" "/dist/css/bootstrap.min.css"
    home_url = reverse("homepage:index")
    venues_url = reverse("venues:list")
    bookings_url = reverse("bookings:list")
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
    return render(request, "homepage/index.html")
