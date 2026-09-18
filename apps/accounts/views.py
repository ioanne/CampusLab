from django.shortcuts import render


def mi_primer_vista(request):
    # En el MVT, ¿Qué es esto? son las Views
    return render(
        request=request,
        template_name="mi_pagina.html",
        context={
            "variable": "Distraidos",
            "datos": ["Valor 1", "Valor 2"]
        }
    )
