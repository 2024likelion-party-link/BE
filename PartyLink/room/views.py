import time
from django.utils.crypto import get_random_string
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import redis

# Redis 설정
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

class CreateRoomView(APIView):
    def post(self, request):
        host_name = request.data.get('host_name')
        if not host_name:
            return Response({"error": "host_name is required."}, status=status.HTTP_400_BAD_REQUEST)

        # 방 ID 생성
        room_id = get_random_string(12)

        # Redis에 방 정보 저장
        room_info_key = f"room:{room_id}:info"
        redis_client.hset(room_info_key, "host_name", host_name)
        host_token = get_random_string(32)
        redis_client.hset(room_info_key, "host_token", host_token)
        redis_client.expire(room_info_key, 3600)

        # 참가자 목록 초기화
        participants_key = f"room:{room_id}:participants"
        redis_client.lpush(participants_key, f"{host_name}:host:True")
        redis_client.expire(participants_key, 3600)

        # 응답
        return Response({
            "room_id": room_id,
            "user_token": host_token
        }, status=status.HTTP_201_CREATED)
    

class GetGamesView(APIView):
    def get(self, request):
        games = [
            {"id": "handGame", "name": "손병호 게임"},
            {"id": "imageGame", "name": "이미지 게임"},
            {"id": "imageGame", "name": "이미지 게임"},
        ]
        return Response({"games": games}, status=status.HTTP_200_OK)

class GetRoomInfoView(APIView):
    def get(self, request, room_id):
        """방 정보 가져오기"""
        room_info_key = f"room:{room_id}:info"
        participants_key = f"room:{room_id}:participants"

        if not redis_client.exists(room_info_key):
            return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)

        # 방 정보 가져오기
        host_name = redis_client.hget(room_info_key, "host_name")
        host_token = redis_client.hget(room_info_key, "host_token")

        # 참가자 정보 가져오기
        participants = redis_client.lrange(participants_key, 0, -1)
        participants_data = [
            {
                "userId": p.decode("utf-8").split(":")[0],
                "nickname": p.decode("utf-8").split(":")[1],
                "is_host": p.decode("utf-8").split(":")[2] == "True"
            }
            for p in participants
        ]

        return Response({
            "room_id": room_id,
            "host_name": host_name.decode("utf-8") if host_name else None,
            "participants": participants_data
        }, status=status.HTTP_200_OK)