from django.core.exceptions import ValidationError

# Предельный размер загружаемого изображения площадки: 2 МБ.
MAX_IMAGE_SIZE = 2 * 1024 * 1024


def validate_image_size(image):
    """Проверка размера файла: слишком большое изображение отклоняется с сообщением об ошибке."""
    if image.size > MAX_IMAGE_SIZE:
        raise ValidationError(
            f"Размер изображения не должен превышать {MAX_IMAGE_SIZE // (1024 * 1024)} МБ."
        )
