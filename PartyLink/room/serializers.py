from rest_framework import serializers
from .models import Room, Participant

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['room_id', 'host_name', 'created_at']

class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = ['nickname', 'role', 'joined_at']
