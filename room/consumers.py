import json
from channels.generic.websocket import AsyncWebsocketConsumer
import redis

redis_client = redis.StrictRedis(host='redis', port=6379, db=0)

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'game_{self.room_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        redis_client.sadd(f"room:{self.room_id}", data['nickname'])

        participants = redis_client.smembers(f"room:{self.room_id}")
        participant_list = list(map(lambda x: x.decode(), participants))

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'participant_update',
                'participants': participant_list,
            }
        )

    async def participant_update(self, event):
        participants = event['participants']
        await self.send(text_data=json.dumps({
            'participants': participants
        }))
