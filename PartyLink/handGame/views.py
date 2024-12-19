from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Game, PlayerState, Round
from room.models import Room, Participant
from .serializers import GameSerializer, PlayerStateSerializer
import random


class StartGameAPIView(APIView):
    def post(self, request, room_id):
        # 방 확인
        room = get_object_or_404(Room, room_id=room_id)
        participants = room.participants.all()

        if len(participants) < 2:
            return Response(
                {"error": "The game requires at least 2 participants."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 게임 생성
        game = Game.objects.create(room=room)
        random_order = list(participants)
        random.shuffle(random_order)

        # 플레이어 상태 초기화
        for participant in random_order:
            PlayerState.objects.create(participant=participant)

        game.start_game()

        return Response({
            "message": "Game started successfully",
            "game": GameSerializer(game).data,
        }, status=status.HTTP_201_CREATED)


class SubmitActionAPIView(APIView):
    def post(self, request, game_id):
        # 게임 확인
        game = get_object_or_404(Game, id=game_id, status="in_progress")
        participant_id = request.data.get("participant_id")
        participant = get_object_or_404(PlayerState, participant__id=participant_id)

        # 플레이어 상태 업데이트
        participant.reduce_finger()

        # 플레이어 탈락 확인
        if participant.fingers == 0:
            game.end_game(participant.participant)
            return Response({
                "message": f"{participant.participant.nickname} has been eliminated!",
                "loser": participant.participant.nickname,
            }, status=status.HTTP_200_OK)

        # 다음 라운드 진행
        game.start_next_round()
        return Response({
            "message": "Action submitted successfully",
            "current_round": game.current_round,
        }, status=status.HTTP_200_OK)


class GameStatusAPIView(APIView):
    def get(self, request, game_id):
        # 게임 확인
        game = get_object_or_404(Game, id=game_id)
        serializer = GameSerializer(game)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PlayerListAPIView(APIView):
    def get(self, request, room_id):
        # 방 내 참가자 확인
        room = get_object_or_404(Room, room_id=room_id)
        players = PlayerState.objects.filter(participant__room=room)
        serializer = PlayerStateSerializer(players, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
