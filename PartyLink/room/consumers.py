import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
import redis

# Redis 설정
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"room_{self.room_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Redis에서 참가자 정보 가져오기
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
            nickname = data.get("nickname")
            user_token = data.get("user_token")  # 클라이언트로부터 user_token을 받아옴
            user_id = str(uuid.uuid4())
            is_host = False

            # 참가자 추가
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
            await self.send(json.dumps({"type": "self_id", "userId": user_id}))

        elif message_type == "select_game":
            game_id = data.get("game_id")
            is_host = await self.is_host(data.get("user_token"))  # 호스트 여부 확인
            if is_host:
                redis_client.set(f"room:{self.room_id}:selected_game", game_id)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "game_selected",
                        "game_id": game_id
                    }
                )
            else:
                await self.send(json.dumps({
                    "type": "error",
                    "message": "Only the host can select the game."
                }))

    async def update_participants(self, event):
        participants = event["participants"]
        await self.send(json.dumps({"type": "participants_update", "participants": participants}))

    async def game_selected(self, event):
        game_id = event["game_id"]
        await self.send(json.dumps({"type": "game_selected", "game_id": game_id}))

    async def add_participant(self, nickname, user_id, is_host):
        participants_key = f"room:{self.room_id}:participants"
        participant_data = f"{user_id}:{nickname}:{is_host}"
        redis_client.lpush(participants_key, participant_data)
        redis_client.expire(participants_key, 3600)  # 1시간 만료

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

    async def is_host(self, user_token):
        """Check if the user is the host of the room."""
        host_token = await self.get_host_token()
        return user_token == host_token

    async def get_host_token(self):
        """Retrieve the host token from Redis."""
        host_info_key = f"room:{self.room_id}:info"
        host_token = redis_client.hget(host_info_key, "host_token")
        return host_token.decode("utf-8") if host_token else None
    
    async def send_participants_to_client(self):
        participants_key = f"room:{self.room_id}:participants"
        participants = redis_client.lrange(participants_key, 0, -1)
        participants_data = [json.loads(p.decode("utf-8")) for p in participants]
        
        await self.send(json.dumps({
            "type": "participants_data",
            "participants": participants_data
        }))
    async def notify_handgame(self):
        participants_key = f"room:{self.room_id}:participants"
        participants = redis_client.lrange(participants_key, 0, -1)
        participants_data = [json.loads(p.decode("utf-8")) for p in participants]

        handgame_group_name = f"handgame_{self.room_id}"
        await self.channel_layer.group_send(
            handgame_group_name,
            {
                "type": "participants_update",
                "participants": participants_data
            }
        )
