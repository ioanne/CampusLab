from django.core.exceptions import ValidationError


def ensure_choice(field, value, choices, message=None):
    if value not in choices.values:
        raise ValidationError(
            {field: message or f"Valor invalido. Opciones: {', '.join(choices.values)}."}
        )
