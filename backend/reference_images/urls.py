from django.urls import path
from reference_images.views import ReferenceImageEnrollAPIView, ReferenceImageDeleteAPIView

app_name = 'reference_images'

urlpatterns = [
    path("<int:user_id>/", ReferenceImageEnrollAPIView.as_view(), name="user_refrence_images"),
    path("user/<int:user_id>/image/<int:image_id>/", ReferenceImageDeleteAPIView.as_view(), name="delete-reference-image"),
]