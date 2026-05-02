from django.urls import path
from access_verification.views import ImageAccessCheckAPIView, AccessHistoryAPIView

app_name = 'access_verification'

urlpatterns = [
    path("check/image/", ImageAccessCheckAPIView.as_view(), name="image"),
    path("history/", AccessHistoryAPIView.as_view(), name="all_records"),
    path("history/<int:pk>/", AccessHistoryAPIView.as_view(), name="single_record"),
]
