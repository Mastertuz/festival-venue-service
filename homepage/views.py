from django.shortcuts import render


def index(request):
    return render(request, "homepage/index.html")


def page_not_found(request, exception):
    """Обработчик 404: страница проекта вместо служебной страницы Django."""
    return render(request, "homepage/404.html", status=404)
