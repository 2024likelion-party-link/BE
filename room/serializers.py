from rest_framework import serializers
from .models import Room, RoomParticipant

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'name', 'host', 'created_at', 'is_active']

class RoomParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomParticipant
        fields = ['id', 'room', 'user', 'nickname', 'joined_at']
