import uuid
import redis
import time
from django.utils.crypto import get_random_string
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Room

# Redis 클라이언트 설정
redis_client = redis.StrictRedis(host="127.0.0.1", port=6379, db=0)


class CreateRoomView(APIView):
    def post(self, request):
        host_name = request.data.get('host_name')
        if not host_name:
            return Response({"error": "host_name is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Room 객체 생성
        room = Room.objects.create(host_name=host_name)

        # 사용자 ID 생성
        user_id = get_random_string(12)

        # Redis에 방 정보 저장
        redis_client.set(f"room:{room.room_id}:info", "created", ex=3600)  # TTL 1시간
        timestamp = time.time()
        redis_client.zadd(f"room:{room.room_id}:participants", {f"{user_id}:{host_name}:True": timestamp})
        redis_client.expire(f"room:{room.room_id}:participants", 3600)  # TTL 1시간

        # 참가자 정보 초기화
        participants_data = [
            {
                "userId": user_id,
                "nickname": host_name,
                "is_host": True
            }
        ]

        # 응답
        return Response({
            "room_id": room.room_id,
            "participants": participants_data
        }, status=status.HTTP_201_CREATED)
    


# 게임 목록 반환
class GetGamesView(APIView):
    def get(self, request):
        games = [
            {"id": "handGame", "name": "손병호 게임"},
            {"id": "imageGame", "name": "이미지 게임"}
        ]
        return Response({"games": games}, status=status.HTTP_200_OK)
    
class GetRoomInfoView(APIView):
    def get(self, request, room_id):
        """방 정보와 선택된 게임 가져오기"""
        room_info_key = f"room:{room_id}:info"
        participants_key = f"room:{room_id}:participants"
        selected_game_key = f"room:{room_id}:selected_game"

        if not redis_client.exists(room_info_key):
            return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)

        # Room 객체에서 방 정보 가져오기
        try:
            room = Room.objects.get(room_id=room_id)
        except Room.DoesNotExist:
            return Response({"error": "Room not found in database"}, status=status.HTTP_404_NOT_FOUND)

        # Redis에서 참가자 정보 가져오기
        participants = redis_client.zrange(participants_key, 0, -1, withscores=True)
        participants_data = [
            {
                "userId": p.decode("utf-8").split(":")[0],
                "nickname": p.decode("utf-8").split(":")[1],
                "is_host": p.decode("utf-8").split(":")[2] == "True"
            }
            for p, _ in participants
        ]

        # 선택된 게임 정보 가져오기
        selected_game = redis_client.get(selected_game_key)
        selected_game = selected_game.decode("utf-8") if selected_game else None

        return Response({
            "room_id": room_id,
            "host_name": host_name.decode("utf-8") if host_name else None,
            "participants": participants_data,
            "selected_game": selected_game
        }, status=status.HTTP_200_OK)
