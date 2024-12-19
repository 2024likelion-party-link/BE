from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Message
from .serializers import MessageSerializer
from room.models import Room
import redis

redis_client = redis.StrictRedis(host="127.0.0.1", port=6379, db=0)

class MessageView(APIView):
    def get(self, request, room_id):
        # 특정 방의 메시지 조회
        try:
            room = Room.objects.get(room_id=room_id)
            messages = Message.objects.filter(room=room)
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Room.DoesNotExist:
            return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, room_id):
        # 특정 방에 메시지 추가
        try:
            room = Room.objects.get(room_id=room_id)
            
            # 사용자 토큰에서 sender를 가져옴
            user_token = request.COOKIES.get("user_token")
            if not user_token:
                return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
            
            sender = redis_client.get(f"user:{user_token}:nickname")
            if not sender:
                return Response({"error": "Invalid token or user not found"}, status=status.HTTP_403_FORBIDDEN)
            
            sender = sender.decode()  # 바이트 데이터를 문자열로 변환
            
            # 메시지 데이터 준비
            data = request.data
            data["room"] = room.id  # 메시지에 방 정보 추가
            data["sender"] = sender  # sender 자동 설정
            
            serializer = MessageSerializer(data=data)

            if serializer.is_valid():
                message = serializer.save()

                # WebSocket 브로드캐스트를 위해 채널 레이어에 메시지 전달
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync

                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"room_{room_id}",
                    {
                        "type": "chat.message",
                        "sender": message.sender,
                        "content": message.content,
                        "timestamp": message.timestamp.isoformat(),
                        "is_self": sender == redis_client.get(f"user:{user_token}:nickname").decode(),  # 본인 확인
                    },
                )

                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Room.DoesNotExist:
            return Response({"error": "Room not found"}, status=status.HTTP_404_NOT_FOUND)
