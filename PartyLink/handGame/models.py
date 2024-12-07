from django.db import models
from room.models import Room, Participant


class HandGame(models.Model):
    room = models.OneToOneField(Room, on_delete=models.CASCADE, related_name="hand_game")
    is_active = models.BooleanField(default=True)
    current_turn = models.ForeignKey(
        Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"HandGame in Room {self.room.room_id}"


class Hand(models.Model):
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name="hand")
    fingers = models.IntegerField(default=5)  # 초기 손가락 개수: 5개

    def __str__(self):
        return f"{self.participant.nickname}: {self.fingers} fingers"
