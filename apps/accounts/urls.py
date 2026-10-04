from django.urls import path

from apps.accounts.views import mi_primer_vista

urlpatterns = [
    path('mi_primer_vista', mi_primer_vista)
]