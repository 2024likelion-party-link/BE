import random
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.layers import get_channel_layer
from channels.generic.websocket import AsyncWebsocketConsumer
import json
import redis
import asyncio

# Redis 설정
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

class HandGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 쿠키에서 user_id 가져오기
        user_id = self.scope['cookies'].get('user_id')
        if not user_id:
            await self.close()
            return

        self.user_id = user_id
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"neverhaveiever_{self.room_id}"

        # 그룹에 추가
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        participants = await self.get_participants()
        await self.send(json.dumps({"type": "participants_update", "participants": participants}, ensure_ascii=False))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

