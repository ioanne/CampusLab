from django.urls import path

from apps.accounts.views import mi_primer_vista

urlpatterns = [
    path(route="mi_pagina", view=mi_primer_vista)
]
