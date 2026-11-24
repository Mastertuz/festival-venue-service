"""Общие вспомогательные классы проекта: примеси для классовых представлений (ПР13)."""


class DataMixin:
    """Примесь для классовых представлений: заголовок страницы, пагинация и контекст.

    Класс записывается первым в списке наследования, например
    ``class BookingListView(DataMixin, ListView)``: тогда его атрибуты и методы находятся
    раньше атрибутов базового представления (порядок MRO).
    """

    # Заголовок страницы по умолчанию; задаётся в классе представления.
    title_page = None

    # Количество записей на странице для классов-списков (ListView).
    paginate_by = 5

    # Дополнительные статические данные для шаблона. Django включает этот словарь в контекст
    # любого классового представления.
    extra_context = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Работаем с копией словаря: запись заголовка в общий словарь класса попала бы в
        # контекст остальных представлений, наследующих примесь.
        self.extra_context = dict(self.extra_context or {})
        # Если заголовок задан, он попадает в контекст через extra_context.
        if self.title_page:
            self.extra_context["title"] = self.title_page

    def get_mixin_context(self, context, **kwargs):
        """Добавить в контекст заголовок страницы и переданные значения.

        Нужен для динамических заголовков, например с номером объекта:
        ``self.get_mixin_context(context, title=f"Бронирование №{self.object.pk}")``.
        """
        if self.title_page:
            context["title"] = self.title_page
        context.update(kwargs)
        return context
