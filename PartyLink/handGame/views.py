from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serlalizers import HandGameSerializer
from .models import HandGame


class HandGameStartAPIView(APIView):
    def post(self, request, room_id):
        # 방 ID로 게임 생성
        game = HandGame.objects.create(room_id=room_id)
        serializer = HandGameSerializer(game)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class HandGameEndAPIView(APIView):
    def post(self, request, room_id):
        # 게임 종료 처리
        try:
            game = HandGame.objects.get(room_id=room_id, is_active=True)
            game.is_active = False
            game.save()
            return Response({"message": "Game ended successfully."}, status=status.HTTP_200_OK)
        except HandGame.DoesNotExist:
            return Response({"error": "Active game not found."}, status=status.HTTP_404_NOT_FOUND)
