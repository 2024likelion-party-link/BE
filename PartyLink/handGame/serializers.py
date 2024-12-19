from rest_framework import serializers
from .models import Game, PlayerState, Round
from room.models import Participant


class PlayerStateSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(source="participant.nickname")

    class Meta:
        model = PlayerState
        fields = ["nickname", "fingers", "is_active"]


class GameSerializer(serializers.ModelSerializer):
    players = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = ["id", "room", "status", "current_round", "loser", "created_at", "updated_at", "players"]

    def get_players(self, obj):
        players = PlayerState.objects.filter(participant__room=obj.room)
        return PlayerStateSerializer(players, many=True).data


class RoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Round
        fields = ["id", "game", "round_number", "current_turn", "created_at"]
