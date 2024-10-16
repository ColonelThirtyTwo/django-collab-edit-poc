from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("<int:pk>/", views.doc, name="detail"),
    path("<int:pk>/history", views.history_list, name="history_list"),
    path("<int:doc_pk>/history/<int:history_pk>", views.history_view, name="history_view"),
]
