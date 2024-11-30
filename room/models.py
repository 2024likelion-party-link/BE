from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Room(models.Model):
    id = models.AutoField(primary_key=True)  # 방 고유 ID
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_rooms')
    room_code = models.CharField(max_length=10, unique=True)  # 방 고유 코드
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # 방 활성화 상태

    def __str__(self):
        return f"{self.id} ({self.room_code})"


class RoomParticipant(models.Model):
    id = models.AutoField(primary_key=True)  # 참가자 고유 ID
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='participants')  # 방 참조
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # 사용자 참조 (비회원일 경우 NULL 허용)
    nickname = models.CharField(max_length=50, unique=True)  # 플레이어 닉네임 (고유)
    joined_at = models.DateTimeField(auto_now_add=True)  # 입장 시간

    def __str__(self):
        return f"{self.nickname} in {self.room.id}"