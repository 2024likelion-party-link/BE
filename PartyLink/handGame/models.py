import uuid
from django.db import models
from room.models import Room, Participant


class Game(models.Model):
    GAME_STATUS_CHOICES = [
        ('waiting', 'Waiting'),       # 대기 상태
        ('in_progress', 'In Progress'),  # 게임 진행 중
        ('finished', 'Finished')     # 게임 종료
    ]

    room = models.OneToOneField(Room, on_delete=models.CASCADE, related_name="game")  # 방과 연결
    status = models.CharField(max_length=20, choices=GAME_STATUS_CHOICES, default='waiting')  # 현재 상태
    current_round = models.PositiveIntegerField(default=0)  # 현재 라운드
    loser = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name="lost_games")  # 패자
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def start_game(self):
        """게임 시작 상태로 전환"""
        self.status = 'in_progress'
        self.save()

    def end_game(self, loser):
        """게임 종료 상태로 전환"""
        self.status = 'finished'
        self.loser = loser
        self.save()

    def start_next_round(self):
        """다음 라운드로 진행"""
        self.current_round += 1
        self.save()

    def __str__(self):
        return f"Game in Room {self.room.id} (Status: {self.status})"


class PlayerState(models.Model):
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name="player_state")  # 참가자
    fingers = models.PositiveIntegerField(default=5)  # 손가락 개수
    is_active = models.BooleanField(default=True)  # 게임에 여전히 참여 중인지 확인
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def reduce_finger(self, amount=1):
        """손가락 개수를 줄임"""
        self.fingers = max(self.fingers - amount, 0)
        self.is_active = self.fingers > 0
        self.save()

    def __str__(self):
        return f"{self.participant.nickname} - {self.fingers} Fingers"


class Round(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="rounds")  # 라운드가 속한 게임
    round_number = models.PositiveIntegerField()  # 라운드 번호
    current_turn = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True, related_name="current_turns")  # 현재 턴의 참가자
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Round {self.round_number} in Game {self.game.id}"
