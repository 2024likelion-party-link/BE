import uuid
from django.db import models

class Room(models.Model):
    room_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    host_name = models.CharField(max_length=100, null=False)  # 반드시 값 필요
    created_at = models.DateTimeField(auto_now_add=True)
