from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("v1/leads/", views.LeadCreateView.as_view(), name="leads"),
    path("v1/clients/", views.ClientListView.as_view(), name="clients"),
    path("v1/clients/<int:pk>/", views.ClientDetailView.as_view(), name="client"),
    path(
        "v1/clients/<int:pk>/interactions/",
        views.InteractionListCreateView.as_view(),
        name="interactions",
    ),
    path("v1/properties/", views.PropertyListView.as_view(), name="properties"),
    path("v1/properties/<str:code>/", views.PropertyDetailView.as_view(), name="property"),
    path("schema/", views.ApiSchemaView.as_view(), name="schema"),
    path("docs/", views.ApiDocsView.as_view(url_name="api:schema"), name="docs"),
]
