from http.cookies import SimpleCookie
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
        # HTTP 헤더에서 Cookie 가져오기
        headers = dict(self.scope["headers"])
        cookie_header = headers.get(b'cookie', b'').decode()

        # 쿠키 파싱
        cookies = SimpleCookie(cookie_header)
        user_id = cookies.get('user_id').value if 'user_id' in cookies else None

        if not user_id:
            await self.send(json.dumps({"type": "error", "message": "User ID not found in cookies."}, ensure_ascii=False))
            await self.close()
            return

        self.user_id = user_id
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"neverhaveiever_{self.room_id}"

        # 그룹에 추가
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # 참가자 업데이트
        participants = await self.get_participants()
        await self.send(json.dumps({"type": "participants_update", "participants": participants}, ensure_ascii=False))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type")

        if message_type == "start":
            await self.start(data)
        elif message_type == "fold":
            await self.handle_fold(data)
        else:
            await self.send_error(f"Unknown message type: {message_type}")

    async def start(self, data):
        participants = await self.get_participants()
        started_key = f"handgame:{self.room_id}:started"

        if len(participants) < 5:
            await self.send_error("Not enough participants to start the game. 5 participants are required.")
            return

        if redis_client.get(started_key):
            await self.send_error("Game already started.")
            return

        redis_client.set(started_key, 1)
        await self.randomize_turn_order()

        # 응답 전송
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "game_started", "message": "Game started successfully!"}
        )

    

    async def get_participants(self):
        participants_key = f"room:{self.room_id}:participants"
        participants = redis_client.lrange(participants_key, 0, -1)
        return [
            {
                "userId": p.decode("utf-8").split(":")[0],
                "nickname": p.decode("utf-8").split(":")[1],
                "is_host": p.decode("utf-8").split(":")[2] == "True"
            }
            for p in participants
        ]
    
    async def randomize_turn_order(self):
        participants = await self.get_participants()
        redis_client.delete(f"room:{self.room_id}:participants")
        random.shuffle(participants)

        for participant in participants:
            participant['fingers'] = 5  # Reset fingers to 5
            redis_client.rpush(f"room:{self.room_id}:participants", json.dumps(participant))

        redis_client.set(f"room:{self.room_id}:turn", 0)

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "turn_update", "turn_user": participants[0], "participants": participants}
        )

    # 에러 응답
    async def send_error(self, error_message):
        await self.send(json.dumps({"type": "error", "message": error_message}, ensure_ascii=False))

    async def handle_question(self, data):
        user_id = data.get("userId")
        question = data.get("question")

        turn_user = await self.get_current_turn_user()
        if turn_user["userId"] != user_id:
            await self.send(json.dumps({"type": "error", "message": "It's not your turn."}))
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "new_question", "question": question, "userId": user_id}
        )

        asyncio.create_task(self.move_to_next_turn(delay=15))

    async def handle_fold(self, data):
        user_id = data.get("userId")
        participants_key = f"room:{self.room_id}:participants"

        participants = redis_client.lrange(participants_key, 0, -1)
        for idx, p in enumerate(participants):
            participant = json.loads(p)
            if participant["userId"] == user_id and participant["fingers"] > 0:
                participant["fingers"] -= 1
                redis_client.lset(participants_key, idx, json.dumps(participant))
                break

        participants = await self.get_participants()
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "update_participants", "participants": participants}
        )

        await self.check_game_end()

    async def handle_undo_fold(self, data):
        user_id = data.get("userId")
        participants_key = f"room:{self.room_id}:participants"

        participants = redis_client.lrange(participants_key, 0, -1)
        for idx, p in enumerate(participants):
            participant = json.loads(p)
            if participant["userId"] == user_id and participant["fingers"] < 5:
                participant["fingers"] += 1
                redis_client.lset(participants_key, idx, json.dumps(participant))
                break

        participants = await self.get_participants()
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "update_participants", "participants": participants}
        )
    
    async def update_participants(self, event):
        participants = event["participants"]
        await self.send(json.dumps({"type": "participants_update", "participants": participants}, ensure_ascii=False))

    async def new_question(self, event):
        question = event["question"]
        user_id = event["userId"]
        await self.send(json.dumps({"type": "new_question", "question": question, "userId": user_id}))

# ...existing code...

    async def move_to_next_turn(self, delay=0):
        if delay:
            await asyncio.sleep(delay)

        participants = await self.get_participants()
        turn_key = f"room:{self.room_id}:turn"
        current_turn = int(redis_client.get(turn_key))

        next_turn = (current_turn + 1) % len(participants)
        redis_client.set(turn_key, next_turn)

        next_user = participants[next_turn]
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "turn_update", "turn_user": next_user, "participants": participants}
        )

    async def turn_update(self, event):
        turn_user = event["turn_user"]
        participants = event["participants"]
        await self.send(json.dumps({"type": "turn_update", "turn_user": turn_user, "participants": participants}, ensure_ascii=False))

# ...existing code...
    
    async def game_started(self, event): 
        await self.send(json.dumps({"type": "game_started", "message": event["message"]}, ensure_ascii=False))


