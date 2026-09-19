from django.db import models
from django.contrib.auth.models import AbstractUser

from apps.core.models import BaseModel


class CustomUser(AbstractUser, BaseModel): # Extendiendo el usuario de django
    nickname = models.CharField(max_length=255)


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

# CustomUser.objects.all() 
# SELECT * FROM USER
# SELECT * FROM USER WHERE id=1

"""
    Los modelos en django se representan con clases.
    Un modelo es una tabla
    Un campo es un atributo del modelo
"""


"""

CustomUser.objects.filter(username="pepito", profile__id=1)


'SELECT "accounts_customuser"."id", "accounts_customuser"."password",
"accounts_customuser"."last_login", "accounts_customuser"."is_superuser",
"accounts_customuser"."username", "accounts_customuser"."first_name",
"accounts_customuser"."last_name", "accounts_customuser"."email",
"accounts_customuser"."is_staff", "accounts_customuser"."is_active",
"accounts_customuser"."date_joined", "accounts_customuser"."delete_on",
"accounts_customuser"."create_on" FROM "accounts_customuser"
INNER JOIN "accounts_studentprofile" ON
("accounts_customuser"."id" = "accounts_studentprofile"."user_id")
WHERE
("accounts_studentprofile"."id" = 1 AND "accounts_customuser"."username"= pepito)'

"""


def create_user(username):
    username = username.lower()
    return CustomUser.objects.create(username=username) # pitufito

def get_user(username):
    username = username.lower()
    return CustomUser.objects.get(username=username) # pitufito
