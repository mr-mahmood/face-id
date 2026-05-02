from django.contrib import admin
from reference_images.models import ReferenceImages

# Register your models here.
@admin.register(ReferenceImages)
class ReferenceImagesAdmin(admin.ModelAdmin):
    model = ReferenceImages

    list_display = ("id", "user", "image")
    search_fields = ("user",)
    ordering = ("id",)

    # disable add / delete / change buttons in admin
    def has_add_permission(self, request):
        return False  # never allow add

    def has_change_permission(self, request, obj=None):
        return False  # never allow editing