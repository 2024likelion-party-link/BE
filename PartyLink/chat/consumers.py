import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
import redis


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        redis_client = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)  # 여기로 이동
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
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
        redis_client = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)  # 여기로 이동
        # 메시지 처리 로직...
