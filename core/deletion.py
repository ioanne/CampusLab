"""Borrado definitivo, con reglas que lo pueden impedir y archivos que se limpian despues.

Cada app decide QUE impide borrar sus entidades (las reglas) y QUE archivos
quedan huerfanos; este modulo solo sabe COMO se borra: preguntar las reglas,
borrar en una transaccion y limpiar el disco recien cuando la base confirmo.
Sumar una regla nueva no obliga a tocar este codigo.
"""
from dataclasses import dataclass
from typing import Protocol

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError


class DeletionRule(Protocol):
    def check(self, instance):
        """Devuelve {campo: mensaje} si el borrado no se puede hacer, o None."""


@dataclass(frozen=True)
class BlockedWhileRelated:
    """Impide el borrado mientras la relacion inversa tenga filas."""

    related_name: str
    field: str
    message: str

    def check(self, instance):
        if getattr(instance, self.related_name).exists():
            return {self.field: self.message}
        return None


def delete_definitively(instance, *, rules=(), files=()):
    """Borra la fila (y lo que cuelga en cascada) si ninguna regla lo impide.

    Los archivos se borran con on_commit: si la transaccion se deshace, el
    disco queda intacto y la fila sigue apuntando a archivos que existen.
    """
    files = [file for file in files if file]
    with transaction.atomic():
        errors = {}
        for rule in rules:
            errors.update(rule.check(instance) or {})
        if errors:
            raise ValidationError(errors)

        try:
            instance.delete()
        except ProtectedError as exc:
            raise ValidationError(
                "No se puede borrar: hay otros datos que dependen de este."
            ) from exc

        transaction.on_commit(lambda: _remove_files(files))


def _remove_files(files):
    for file in files:
        file.storage.delete(file.name)
