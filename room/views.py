from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Room
from .serializers import RoomSerializer
import redis


redis_client = redis.StrictRedis(host="127.0.0.1", port=6379, db=0)

class CreateRoomView(APIView):
    def post(self, request):
        host_name = request.data.get('host_name')

        # host_name 값 검증
        if not host_name:
            return Response(
                {"error": "host_name is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Room 객체 생성
        room = Room.objects.create(host_name=host_name)

  # Redis에 호스트 정보 저장
        redis_client.set(f"room:{room.room_id}:host", host_name)

        return Response({"room_id": str(room.room_id)}, status=status.HTTP_201_CREATED)


class JoinRoomView(APIView):
    def post(self, request, room_id):
        nickname = request.data.get('nickname')
        if redis_client.sadd(f"room:{room_id}", nickname):
            return Response({"message": "Joined room"}, status=status.HTTP_200_OK)
        return Response({"error": "Failed to join room"}, status=status.HTTP_400_BAD_REQUEST)

class GetParticipantsView(APIView):
    def get(self, request, room_id):
        participants = redis_client.smembers(f"room:{room_id}")
        return Response({"participants": list(map(lambda x: x.decode(), participants))})
