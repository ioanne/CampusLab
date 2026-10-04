from django.db import models
from django.contrib.auth.models import AbstractUser

# CustomUser
# StudentProfile

class CustomUser(AbstractUser): # Estoy extendiendo el usuario de django
    # Lo extiendo para poder agregarlo mis propios atributos y métodos AL MODELO USER DE DJANGO
    phone_number = models.CharField(max_length=255) # campo - phone_number

# Este va a estar relacionado con CustomUser
class StudentProfile(models.Model): # tabla - StudentProfile
    bio = models.CharField(max_length=255) # campo - bio

'''
lOS MODELOS en django se representan con clases 
Un modelo es una tabla
Un campo es un atributo del modelo
'''