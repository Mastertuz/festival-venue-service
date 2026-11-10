from django import forms

from .models import Venue


class VenueForm(forms.ModelForm):
    """Форма создания и редактирования площадки с загрузкой изображения.

    Поля берутся из модели Venue. Служебные поля (slug, is_large) в форму не входят: slug
    формируется при сохранении, is_large вычисляет база данных. Для загрузки файла в
    представление передаётся request.FILES, а HTML-форме нужен enctype="multipart/form-data".
    """

    class Meta:
        model = Venue
        fields = ["name", "capacity", "image"]
        labels = {
            "name": "Название площадки",
            "capacity": "Вместимость",
            "image": "Изображение",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            # accept подсказывает браузеру, какие файлы показывать; проверка выполняется на сервере.
            "image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Для PositiveIntegerField Django ставит min="0"; ноль запрещён правилом модели.
        self.fields["capacity"].widget.attrs["min"] = 1

    def clean_capacity(self):
        """Проверка отдельного поля: вместимость должна быть положительной."""
        capacity = self.cleaned_data["capacity"]
        if capacity <= 0:
            raise forms.ValidationError("Вместимость должна быть больше нуля.")
        return capacity
