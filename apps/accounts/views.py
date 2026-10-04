from django.shortcuts import render

# Create your views here.
# Vista basada en funcion, que NO hay que usar, sino, vistas basadas en CLASES.

# esto va agregado en urls.py en este directorio
"""
def mi_primer_vista(request):
    return render("Hola!")
"""


# 3° le está pasando la funcion a django para que django la ejecute
# y le va a decir, vamos a crear un render, del request que recibimos con este template


# En MVT que es esto?
# es el controlador, que en django se llama Views.
# cuando matchea, ejecuta la lógica de la vista. que seria la lógica de negocio
# esta logica de vista, está llamando a la logica de TEMPLATE

# tenemos una vista, la función, que recibe una solicitud y deuvelve la renderizacion de render() con todos los parametros que tiene.
# lo que hace es renderizar, el template jaja.html, con los valores que le paso en el context

# quien recibe la solicitud, es django. django usa una funcion creada por nosotros, a la fn creada por nosotros le pasa los datos que vienen del request, cómo django recibe la solicitud, va a tener los valores para pasarle del req
def mi_primer_vista(request):
    # parametros posicionales
    return render(
        request,
        "jaja.html",
        # le paso en el contexto, los datos
        context={
            "mi_variable": "el valor de mi variable para el template",
            "datos": ["Valor1", "Valor 2"],
        },
    )


def suma(a, b):
    return a + b


def resta(a, b):
    return a - b


# diccionario
operacion = {
    "suma": suma,
    "resta": resta,
}
operacion["suma"](2, 5)
operacion["resta"](2, 5)
