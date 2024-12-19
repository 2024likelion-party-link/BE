import uuid
from django.db import models

class Room(models.Model):
    room_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    host_name = models.CharField(max_length=100, null=False)  # Host name is required
    created_at = models.DateTimeField(auto_now_add=True)

class Participant(models.Model):
    ROLE_CHOICES = [
        ('host', 'Host'),
        ('participant', 'Participant'),
    ]

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='participants')
    nickname = models.CharField(max_length=100, null=False)  # Nickname is required
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='participant')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('room', 'nickname')  # Unique nickname within a room

    def __str__(self):
        return f"{self.nickname} ({self.role}) in Room {self.room.room_id}"
