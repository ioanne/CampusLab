from django.urls import path

from apps.accounts.views import mi_primer_vista

# 1° carga este cuando levanta django 
# lo carga una vez sola, genera la vista con las urls
urlpatterns = [
    # la funcion de la vista a renderizar se pasa sin ejecutar
    # ingreso, requiero, solicito una url, matchea con alguna del listado, y cuando matchea, llama a la funcion que esta puesta para esa url, que es mi_primer_vista
    path('mi_primer_vista', mi_primer_vista)
]