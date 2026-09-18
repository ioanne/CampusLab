from django.db import models
from django.contrib.auth.models import AbstractUser

from apps.core.models import BaseModel


class CustomUser(AbstractUser, BaseModel): # Extendiendo el usuario de django
    pass


class StudentProfile(BaseModel): # --> tabla
    bio = models.CharField(max_length=255) # --> campo

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.DO_NOTHING,
        related_name="profile"
    )


# pepito = CustomUser.objects.get(id=1)
# pepito.delete() # --> error.


# pepito.profile.delete()
# pepito.delete() # --> funciona.

"""
    Los modelos en django se representan con clases.
    Un modelo es una tabla
    Un campo es un atributo del modelo
"""