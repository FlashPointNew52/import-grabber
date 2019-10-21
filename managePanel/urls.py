from django.urls import path

from .views import *

urlpatterns = [
    path('', settings),
    path('cities/', settingsCities),
    path('mediasimport/', SettingsMediasImport.as_view()),
    path('medialist/', SettingsMediaList.as_view()),
    path('elastic/', SettingsElastic.as_view()),
    path('createIndex', CreateIndex.as_view()),
    path('deleteIndex', DeleteIndex.as_view()),
    path('deleteData', DeleteData.as_view()),
    path('addCity', AddCity.as_view()),
    path('addMedia', AddMedia.as_view()),
    path('addMediasImport', AddMediaImport.as_view()),
    path('setActiveMedia', SetActiveMedia.as_view())
]
