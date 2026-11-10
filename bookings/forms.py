from django import forms
from django.utils import timezone

from bookings.models import Booking
from festivals.models import Festival, Organizer
from venues.models import Venue

# Допустимые значения параметра sort и подписи для списка выбора. Соответствие значений полям
# модели задаёт словарь SORT_FIELDS в bookings/views.py.
SORT_CHOICES = [
    ("date", "Дате"),
    ("venue", "Площадке"),
    ("festival", "Фестивалю"),
    ("organizer", "Организатору"),
]

DIRECTION_CHOICES = [
    ("asc", "По возрастанию"),
    ("desc", "По убыванию"),
]


class BookingFilterForm(forms.Form):
    """Форма фильтрации списка бронирований; данные приходят GET-запросом.

    Это обычная форма (forms.Form): она проверяет параметры и не создаёт объекты модели.
    Имена полей совпадают с GET-параметрами списка, поэтому адреса вида
    /bookings/?venue=1&sort=date продолжают работать. Номер страницы (page) относится к
    пагинации и в форму не входит.
    """

    # В подписях полей двоеточие не нужно: подписи выводятся шаблоном отдельно.
    label_suffix = ""

    q = forms.CharField(
        required=False,
        max_length=100,
        label="Поиск",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "фестиваль, площадка, организатор"}
        ),
    )
    # Тип date включает в браузере календарь, формат значения — ГГГГ-ММ-ДД.
    date = forms.DateField(
        required=False,
        label="Дата фестиваля",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "class": "form-control"}),
        error_messages={"invalid": "Укажите корректную дату."},
    )
    # ModelChoiceField принимает только идентификатор существующего объекта из queryset.
    venue = forms.ModelChoiceField(
        queryset=Venue.objects.order_by("name"),
        required=False,
        label="Площадка",
        empty_label="Все площадки",
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={"invalid_choice": "Выберите площадку из списка."},
    )
    organizer = forms.ModelChoiceField(
        queryset=Organizer.objects.order_by("name"),
        required=False,
        label="Организатор",
        empty_label="Все организаторы",
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={"invalid_choice": "Выберите организатора из списка."},
    )
    sort = forms.ChoiceField(
        required=False,
        choices=SORT_CHOICES,
        initial="date",
        label="Сортировать по",
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={"invalid_choice": "Выберите вариант сортировки из списка."},
    )
    dir = forms.ChoiceField(
        required=False,
        choices=DIRECTION_CHOICES,
        initial="asc",
        label="Порядок",
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={"invalid_choice": "Выберите порядок сортировки из списка."},
    )
    active = forms.BooleanField(
        required=False,
        label="Только активные",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )


class BookingForm(forms.ModelForm):
    """Форма создания и редактирования бронирования (ModelForm: поля берутся из модели).

    Пользователь выбирает фестиваль и площадку. Дата бронирования равна дате проведения
    фестиваля, поэтому отдельного поля даты нет. Статус в форму не входит: новое бронирование
    получает значение по умолчанию (активно), а менять статус можно только отдельной операцией
    (отмена). Правило «одна площадка — одно активное бронирование на дату» проверяет
    Booking.clean(): ModelForm вызывает его при is_valid(), и ошибка попадает в общие ошибки
    формы (non_field_errors).
    """

    class Meta:
        model = Booking
        # Поля перечислены явно: fields = "__all__" открыл бы и служебный статус.
        fields = ["festival", "venue"]
        labels = {
            "festival": "Фестиваль",
            "venue": "Площадка",
        }
        help_texts = {
            "festival": "Дата бронирования равна дате проведения фестиваля.",
            "venue": "На эту дату у площадки не должно быть другого активного бронирования.",
        }
        widgets = {
            "festival": forms.Select(attrs={"class": "form-select"}),
            "venue": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # В списках выбора показываются дата фестиваля и вместимость площадки.
        self.fields["festival"].queryset = Festival.objects.order_by("date", "pk")
        self.fields["festival"].label_from_instance = lambda festival: (
            f"{festival.name} — {festival.date:%d.%m.%Y}"
        )
        self.fields["venue"].queryset = Venue.objects.order_by("name")
        self.fields["venue"].label_from_instance = lambda venue: (
            f"{venue.name} ({venue.capacity} мест)"
        )

    def clean_festival(self):
        """Проверка отдельного поля: нельзя бронировать площадку на прошедшую дату."""
        festival = self.cleaned_data["festival"]
        # Сегодняшняя дата разрешена; текущую дату берём с учётом часового пояса проекта.
        if festival.date < timezone.localdate():
            raise forms.ValidationError(
                "Нельзя создать бронирование на прошедшую дату: фестиваль уже состоялся."
            )
        return festival
