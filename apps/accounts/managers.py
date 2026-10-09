from django.contrib.auth.base_user import BaseUserManager
from django.db import models


class UserQuerySet(models.QuerySet):
    """Filtros reutilizables sobre usuarios.

    Cada metodo devuelve otro queryset, asi se pueden encadenar:
    User.objects.active().with_role(UserRole.TEACHER).
    """

    def active(self):
        return self.filter(is_active=True)

    def with_role(self, role):
        return self.filter(role=role)

    def search(self, text):
        return self.filter(
            models.Q(first_name__icontains=text)
            | models.Q(last_name__icontains=text)
            | models.Q(email__icontains=text)
        )


# from_queryset suma los metodos del queryset al manager, sin perder lo que ya
# hacia BaseUserManager (crear usuarios y superusuarios).
class UserManager(BaseUserManager.from_queryset(UserQuerySet)):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio.")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        # El import va aca adentro y no arriba: models.py importa este archivo,
        # y que los dos se importen arriba seria un import circular.
        from apps.accounts.models import UserRole

        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("role") != UserRole.ADMIN:
            raise ValueError("El superusuario debe tener rol ADMIN.")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True.")

        return self.create_user(email, password, **extra_fields)
