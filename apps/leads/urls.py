from django.urls import path

from . import views

app_name = "leads"

urlpatterns = [
    path("imoveis/<slug:slug>/contato/", views.create_lead, name="create"),
]
