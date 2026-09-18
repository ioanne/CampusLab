from django.db import models

import datetime



class BaseModel(models.Model):
    class Meta:
        abstract = True

    delete_on = models.DateTimeField(null=True)
    create_on = models.DateTimeField(auto_now=datetime.time)
