"""Traduccion de errores de negocio a errores HTTP.

Los services no saben que existe HTTP: cuando algo no cumple una regla levantan
un ValidationError de Django. Este es el unico lugar donde ese error se convierte
en una respuesta 400 con "detail" (texto) y "errors" (mensajes por campo).
"""
from django.core.exceptions import NON_FIELD_ERRORS
from ninja.errors import HttpError

NON_FIELD_ERRORS_KEY = "non_field_errors"


class ValidationHttpError(HttpError):
    def __init__(self, detail, errors):
        super().__init__(400, detail)
        self.errors = errors


def validation_error(exc):
    """Devuelve el error 400 equivalente a un ValidationError."""
    if hasattr(exc, "message_dict"):
        errors = {
            NON_FIELD_ERRORS_KEY if campo == NON_FIELD_ERRORS else campo: list(mensajes)
            for campo, mensajes in exc.message_dict.items()
        }
        detail = "; ".join(f"{campo}: {' '.join(mensajes)}" for campo, mensajes in errors.items())
    else:
        errors = {NON_FIELD_ERRORS_KEY: list(exc.messages)}
        detail = " ".join(exc.messages)
    return ValidationHttpError(detail, errors)


def validation_error_handler(api):
    def handler(request, exc):
        return api.create_response(
            request, {"detail": exc.message, "errors": exc.errors}, status=exc.status_code
        )

    return handler
