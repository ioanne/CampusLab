"""Reglas de contrasena segura; cuales se exigen lo decide AUTH_PASSWORD_VALIDATORS."""
import string

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class LetterAndDigitValidator:
    def validate(self, password, user=None):
        has_letter = any(char.isalpha() for char in password)
        has_digit = any(char in string.digits for char in password)
        if not (has_letter and has_digit):
            raise ValidationError(
                "La contraseña debe combinar letras y numeros.",
                code="password_no_letter_and_digit",
            )

    def get_help_text(self):
        return "La contraseña debe combinar letras y numeros."


def ensure_strong_password(password, user=None):
    """Corre los validadores configurados y deja sus errores bajo "password"."""
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        raise ValidationError({"password": exc.messages}) from exc
