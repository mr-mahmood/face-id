from rest_framework import serializers
from core.exceptions import APIError, RefImageError
from reference_images.models import ReferenceImages


class ReferenceImagesSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    image = serializers.ImageField()
    
    class Meta:
        model = ReferenceImages
        fields = ["id", "image"]
        read_only_fields = ["id"]
            
    def validate_image(self, value):
        if not value or value.size == 0:
            raise APIError(RefImageError.INVALID_IMAGE)
        return value
