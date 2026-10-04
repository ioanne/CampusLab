"""
URL configuration for CampusLab project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

# 2° genera ESTA LISTA con las urls 
# queda listo para que yo lo llame, cuando lo llame va a pasar por el motor interno de django y ahi le va a preguntar a qué lugar, vista queres ir. 
# el donde queres ir lo lee de la url que le estoy requesteando
urlpatterns = [
    path('admin/', admin.site.urls),
    # Que de la app accounts incluya las urls
    path('accounts/', include('apps.accounts.urls')),
]
