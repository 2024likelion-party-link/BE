from rest_framework import serializers
from .models import HandGame, Hand

class HandGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandGame
        fields = ['id', 'room', 'current_turn', 'is_active', 'created_at']

class HandStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hand
        fields = ['participant', 'fingers']
