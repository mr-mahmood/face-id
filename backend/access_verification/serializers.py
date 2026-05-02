from rest_framework import serializers
from access_verification.models import AccessHistory, AccessHistoryImage
from areas.models import Area
from users.models import User
from users.serializers import UserProfileSerializer
from core.exceptions import APIError, RefImageError
from gates.serializers import GateSerializer
from gates.models import Gate
from areas.serializers import AreaSerializer

class ImageAccessCheckSerializer(serializers.Serializer):
    gate = serializers.IntegerField()
    images = serializers.ListField(
        child=serializers.ImageField()
    )
    
    class Meta:
        fields = ["images", "gate"]
            
    def validate_images(self, value):
        for image in value:
            if not image or image.size == 0:
                raise APIError(RefImageError.INVALID_IMAGE)
        return value
    
    def validate_gate(self, value):
        Gate.get_gate(value)
        return value


class AccessHistoryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessHistoryImage
        fields = ['id', 'image', 'order']


class AccessHistorySerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    gate = GateSerializer(read_only=True)
    area = AreaSerializer(read_only=True)
    images = AccessHistoryImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = AccessHistory
        fields = [
            "id",
            "user",
            "gate",
            "area",
            "status",
            "reason",
            "images",
            "confidence",
            "timestamp"
        ]
        read_only_fields = [
            "id",
            "user",
            "gate",
            "area",
            "status",
            "reason",
            "images",
            "confidence",
            "timestamp"
        ]
        

# Lightweight serializers with explicit field definitions
class AccessCheckUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'employe_number', 'role']
        # Explicitly set these as the only fields
        extra_kwargs = {
            'id': {'read_only': True},
            'first_name': {'read_only': True},
            'last_name': {'read_only': True},
            'employe_number': {'read_only': True},
            'role': {'read_only': True}
        }


class AccessCheckGateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gate
        fields = ['id', 'name', 'role']
        extra_kwargs = {
            'id': {'read_only': True},
            'name': {'read_only': True},
            'role': {'read_only': True}
        }


class AccessCheckAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ['id', 'name']
        extra_kwargs = {
            'id': {'read_only': True},
            'name': {'read_only': True}
        }


class LightAccessHistorySerializer(serializers.ModelSerializer):
    """Lightweight serializer specifically for access check response"""
    user = AccessCheckUserSerializer(read_only=True)
    gate = AccessCheckGateSerializer(read_only=True)
    area = AccessCheckAreaSerializer(read_only=True)
    images = AccessHistoryImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = AccessHistory
        fields = [
            "id",
            "user",
            "gate",
            "area",
            "status",
            "images",
            "confidence",
            "timestamp"
        ]