from django.db import models
from django.db.models import QuerySet
from areas.models import Area
from core.exceptions import APIError, AccessHistoryError
from gates.models import Gate
from users.models import User
from datetime import datetime


class AccessHistory(models.Model):
    class Status(models.TextChoices):
        ALLOWED = "ALLOWED", "Allowed"
        DENIED = "DENIED", "Denied"

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)
    gate = models.ForeignKey(Gate, null=True, blank=True, on_delete=models.PROTECT)
    area = models.ForeignKey(Area, null=True, blank=True, on_delete=models.PROTECT) 
    status = models.CharField(max_length=20, blank=True, choices=Status.choices)
    reason = models.TextField(blank=True)
    confidence = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'access_history'
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["gate"]),
            models.Index(fields=["timestamp"]),
        ]
        ordering = ["-timestamp"]


    def __str__(self):
        user_number = self.user.employe_number if self.user else "UNKNOWN"
        gate_name = self.gate.name if self.gate else "UNKNOWN"
        area_name = self.gate.area.name if self.gate and self.gate.area else "UNKNOWN"

        return (
            f"{user_number} -> "
            f"area: {area_name}, gate: {gate_name} -> "
            f"{self.status}"
        )
    
    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("AccessEvent is append-only and cannot be updated.")
        
        self.area = self.gate.area
            
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Disable deletion."""
        raise ValueError("AccessEvent is append-only and cannot be deleted")
    
    @classmethod
    def get_access_history(cls, access_id:int, current_user:User) -> 'AccessHistory | None':
        try:
            access = cls.objects.get(id=access_id)
        except:
            raise APIError(AccessHistoryError.ACCESS_HISTORY_NOT_EXIST)
        
        # SUPER: can see everything
        if current_user.role == User.Role.SUPER:
            return access
        
        # MANAGER: can see their own + ADMIN + EMPLOYE
        if current_user.role == User.Role.MANAGER:
            forbidden_roles = [User.Role.MANAGER, User.Role.SUPER]
            if access.user != current_user and access.user.role in forbidden_roles:
                raise APIError(AccessHistoryError.ACCESS_HISTORY_NOT_EXIST)
            return access
        
        # ADMIN: can see their own + EMPLOYE
        if current_user.role == User.Role.ADMIN:
            forbidden_roles = [User.Role.ADMIN, User.Role.MANAGER, User.Role.SUPER]
            if access.user != current_user and access.user.role in forbidden_roles:
                raise APIError(AccessHistoryError.ACCESS_HISTORY_NOT_EXIST)
            return access
        
        # EMPLOYE: can only see their own records
        if current_user.role == User.Role.EMPLOYE:
            if access.user != current_user:
                raise APIError(AccessHistoryError.ACCESS_HISTORY_NOT_EXIST)
            return access

    @classmethod
    def get_all_access_history(cls, current_user: User) ->  QuerySet['AccessHistory'] | None:
        if current_user.role == User.Role.SUPER:
            return cls.objects.all()
        elif current_user.role == User.Role.MANAGER:
            return cls.objects.filter(
                models.Q(user=current_user) | 
                ~models.Q(user__role__in=[User.Role.MANAGER, User.Role.SUPER])
            )
        elif current_user.role == User.Role.ADMIN:
            return cls.objects.filter(
                models.Q(user=current_user) | 
                ~models.Q(user__role__in=[User.Role.ADMIN, User.Role.MANAGER, User.Role.SUPER])
            )
        elif current_user.role == User.Role.EMPLOYE:
            return cls.objects.filter(
                models.Q(user=current_user)
            )
    
    
    
def access_history_path(instance, filename):
    ext = filename.split('.')[-1]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
    new_filename = f"{timestamp}.{ext}"
    user_id = instance.access_history.user.id if instance.access_history.user else "unknown"
    access_id = instance.access_history.id
    return f"access-history/{user_id}/{access_id}/{new_filename}"
  
class AccessHistoryImage(models.Model):
    access_history = models.ForeignKey(
        AccessHistory, 
        on_delete=models.CASCADE, 
        related_name='images'
    )
    image = models.ImageField(upload_to=access_history_path)
    order = models.IntegerField(default=0)  # To maintain the sequence of images
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'access_history_images'
        ordering = ['order']