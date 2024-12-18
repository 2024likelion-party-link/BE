import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
import redis
import random
from django.conf import settings

redis_client = redis.StrictRedis(
    host=getattr(settings, 'REDIS_HOST', 'localhost'),
    port=getattr(settings, 'REDIS_PORT', 6379),
    db=0
)

class HandGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"handgame_{self.room_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Room 참가자 목록 가져오기
        participants = await self.get_participants()
        await self.send(json.dumps({
            "type": "participants_update",
            "participants": participants
        }))


    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type")

        if message_type == "join":
            user_id = data.get("user_id")  # 클라이언트에서 전달받은 user_id
            nickname = data.get("nickname")

            # Redis에서 user_id가 존재하는지 확인
            participants_key = f"handgame:{self.room_id}:participants"
            existing_participant = next(
                (json.loads(p.decode("utf-8")) for p in redis_client.lrange(participants_key, 0, -1)
                 if json.loads(p.decode("utf-8"))["userId"] == user_id),
                None
            )

            if existing_participant:
                # 기존 사용자 정보 사용
                user_id = existing_participant["userId"]
                nickname = existing_participant["nickname"]
                is_host = existing_participant["is_host"]
            else:
                # 새로운 사용자 정보 생성
                user_id = user_id or str(uuid.uuid4())
                # is_host = len(await self.get_participants()) == 0  # 첫 참가자는 호스트
                await self.add_participant(nickname, user_id, is_host)

            # 참가자 목록 갱신
            participants = await self.get_participants()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "update_participants",
                    "participants": participants
                }
            )

            # 참가자에게 자신 정보 전송
            await self.send(json.dumps({
                "type": "self_id",
                "userId": user_id
            }))

    async def update_participants(self, event):
        participants = event["participants"]
        await self.send(json.dumps({
            "type": "participants_update",
            "participants": participants
        }))


    async def game_started(self, event):
        await self.send(json.dumps({
            "type": "game_started",
            "order": event["order"]
        }))

    async def round_update(self, event):
        await self.send(json.dumps({
            "type": "round_update",
            "current_round": event["current_round"]
        }))

    async def game_ended(self, event):
        await self.send(json.dumps({
            "type": "game_ended",
            "loser": event["loser"]
        }))

    async def add_participant(self, nickname, user_id, is_host):
        participants_key = f"handgame:{self.room_id}:participants"
        participant_data = {
            "userId": user_id,
            "nickname": nickname,
            "is_host": is_host
        }
        redis_client.lpush(participants_key, json.dumps(participant_data))
        redis_client.expire(participants_key, 3600)  # 만료 시간 설정

    async def get_participants(self):
        participants_key = f"room:{self.room_id}:participants"  # Room 앱의 참가자 키를 사용
        participants = redis_client.lrange(participants_key, 0, -1)
        participants_list = []
        for p in participants:
            try:
                # Redis에서 가져온 데이터를 JSON으로 변환
                participants_list.append(json.loads(p.decode("utf-8")))
            except json.JSONDecodeError as e:
                print(f"Error decoding participant data: {p}, Error: {e}")
                continue  # JSON 형식이 아닌 데이터는 무시
        return participants_list



    async def send_participants_to_game(self):
        participants_key = f"room:{self.room_id}:participants"
        participants = redis_client.lrange(participants_key, 0, -1)
        participants_data = [json.loads(p.decode("utf-8")) for p in participants]
        
        # HandGame 그룹에 참가자 정보 전달
        handgame_group_name = f"handgame_{self.room_id}"
        await self.channel_layer.group_send(
            handgame_group_name,
            {
                "type": "participants_update",
                "participants": participants_data
            }
        )
        
    
