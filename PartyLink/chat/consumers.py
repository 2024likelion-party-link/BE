import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
import redis

# Redis 클라이언트 설정
redis_client = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """WebSocket 연결 설정"""
        self.room_id = self.scope["url_route"]["kwargs"].get("room_id")
        self.room_group_name = f"room_{self.room_id}"

        if not self.room_id:
            await self.close()
            return

        # 그룹에 참가
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        """WebSocket 연결 종료"""
        # 그룹에서 제거
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """WebSocket 메시지 처리"""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(json.dumps({"error": "Invalid JSON format"}))
            return

        # 쿠키에서 user_id 확인
        user_id = self.scope["cookies"].get("user_id")
        print("Cookies:", self.scope["cookies"])  # 디버깅용
        print("User ID:", user_id)  # 디버깅용

        if not user_id:
            await self.send(json.dumps({"error": "Authentication required"}))
            return

        # Redis에서 사용자 닉네임 가져오기
        sender_key = f"user:{user_id}:nickname"
        sender = redis_client.get(sender_key)

        if not sender:
            await self.send(json.dumps({"error": "Invalid user_id or nickname not found"}))
            return

        sender = sender.decode("utf-8")  # Redis 값 디코딩

        content = data.get("content")
        if not content:
            await self.send(json.dumps({"error": "Content is required"}))
            return

        # 그룹에 메시지 브로드캐스트
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "sender": sender,
                "content": content,
            },
        )

    async def chat_message(self, event):
        """그룹 메시지를 WebSocket으로 전송"""
        await self.send(
            text_data=json.dumps(
                {
                    "sender": event["sender"],
                    "content": event["content"],
                    "timestamp": event.get("timestamp", ""),
                }
            )
        )

# Django settings.py에 설정 추가 (필요 시 확인)
# REDIS_HOST = 'localhost'
# REDIS_PORT = 6379
# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels_redis.core.RedisChannelLayer",
#         "CONFIG": {
#             "hosts": [(REDIS_HOST, REDIS_PORT)],
#         },
#     },
# }

# Redis에서 데이터 저장 예제 (테스트용 코드)
# redis_client.set("user:123:nickname", "장")
