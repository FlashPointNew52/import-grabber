"""importApp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
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
from django.urls import path
from django.urls import include
from django.views.generic.base import RedirectView
from .views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('', RedirectView.as_view(url='info', permanent=False), name='index'),
    path('info/', Main.as_view()),
    path('test/', Test.as_view()),
    path('execute/', Execute.as_view()),
    path('findHistory/', FindHistory.as_view()),
    path('settings/', include('managePanel.urls')),
    path('import/', RedirectView.as_view(url='control', permanent=False), name='index'),
    path('import/control', Control.as_view()),
    path('import/jobs', Jobs.as_view()),
    path('import/statistic', Statistic.as_view()),
    path('import/history', History.as_view()),
    path('import/proxy', ProxyList.as_view()),
    path('import/results', Results.as_view()),
    path('import/errors', Errors.as_view()),

]
