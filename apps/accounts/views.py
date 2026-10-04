from django.shortcuts import render

# Create your views here.
# Vista basada en funcion, que NO hay que usar, sino, vistas basadas en CLASES.

# esto va agregado en urls.py en este directorio
def mi_primer_vista(request):
    return render("Hola!")