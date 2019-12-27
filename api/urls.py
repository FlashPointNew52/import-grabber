from django.urls import path

from .views import *

urlpatterns = [
    path('offers/', offers_list),
]
