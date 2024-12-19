from http.cookies import SimpleCookie
import random
import time
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.layers import get_channel_layer
from channels.generic.websocket import AsyncWebsocketConsumer
import json
import redis
import asyncio
import os

# Redis 설정
redis_client = redis.StrictRedis(host=os.getenv('REDIS_HOST'), port=int(os.getenv('REDIS_PORT', 6379)), password=os.getenv('REDIS_PASSWORD', None), db=0)

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

        if message_type == "start": # 게임 시작
            await self.start(data)
        elif message_type == "fold": # 손가락 접기
            await self.handle_fold(data)
        elif message_type == "undo_fold": # 손가락 펴기
            await self.handle_undo_fold(data)
        elif message_type == "chat": #  채팅 보내기기
            await self.make_chat(data)
        elif message_type == "chat_list": # 채팅 목록
            await self.chat_list()
        elif message_type == "next_turn": # 다음 차례 사람으로 넘어가기
            await self.move_to_next_turn()
        elif message_type == "update_participants": # 참가자 업데이트
            await self.update_participants(data)
        else:
            await self.send_error(f"Unknown message type: {message_type}")

    # 게임 시작
    async def start(self, data):
        participants = await self.get_participants()
        started_key = f"handgame:{self.room_id}:started" # 게임 시작 여부를 저장하는 키

        # if len(participants) < 5: # 5명 이상 참가자가 있어야 게임 시작 가능
        #     await self.send_error("Not enough participants to start the game. 5 participants are required.")
        #     return

        if redis_client.get(started_key): # 게임이 이미 시작되었는지 확인
            await self.send_error("Game already started.")
            return

        redis_client.set(started_key, 1) # 게임 시작 플래그 설정
        await self.randomize_turn_order()

        # 응답 전송
        await self.channel_layer.group_send( # 모든 참가자에게 게임 시작 메시지 전송
            self.room_group_name,
            {"type": "game_started", "message": "Game started successfully!"}
        )

    
    # 처음에 참가자 목록 가져오기
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
    
    async def participants(self):
        participants_key = f"room:{self.room_id}:participants"
        participants = redis_client.lrange(participants_key, 0, -1)
        return [
            {
                "userId": p.decode("utf-8").split(":")[0],
                "nickname": p.decode("utf-8").split(":")[1],
                "is_host": p.decode("utf-8").split(":")[2] == "True",
                "fingers": p.decode("utf-8").split(":")[3]
            }
            for p in participants
        ]
    # 참가자들 목록 랜덤으로, 손가락 개수 초기화
    async def randomize_turn_order(self):
        participants = await self.get_participants()
        redis_client.delete(f"room:{self.room_id}:participants")
        random.shuffle(participants) # 참가자 목록 섞기

        for participant in participants:
            participant['fingers'] = 5  # 참가자의 손가락 개수 초기화
            redis_client.rpush(f"room:{self.room_id}:participants", json.dumps(participant))

        redis_client.set(f"room:{self.room_id}:turn", 0)

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "turn_update", "turn_user": participants[0], "participants": participants}
        )

    async def update_participants(self, event):
        participants_key = f"room:{self.room_id}:participants"
        participants = redis_client.lrange(participants_key, 0, -1)
        print(f"Participants fetched from Redis: {participants}")  # Redis에서 참가자 목록 확인

        # JSON 디코딩 후 클라이언트에 전송
        participants = [
            json.loads(p.decode("utf-8")) for p in participants
        ]
        await self.send(json.dumps({
            "type": "participants_update",
            "participants": participants
        }, ensure_ascii=False))


    # 에러 응답
    async def send_error(self, error_message):
        await self.send(json.dumps({"type": "error", "message": error_message}, ensure_ascii=False))

    async def game_started(self, event): 
        await self.send(json.dumps({"type": "game_started", "message": event["message"]}, ensure_ascii=False))

    async def move_to_next_turn(self):

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

    async def game_end(self, event):
        loser = event["loser"]
        ranking = event["ranking"]
        message = event["message"]
    
    # 게임 종료 메시지 전송 (패배자와 순위 포함)
        await self.send(json.dumps(
        {
            "type": "game_end",
            "loser": loser,
            "ranking": ranking,
            "message": message
        },
        ensure_ascii=False
        ))

    async def check_game_end(self):
        participants_key = f"room:{self.room_id}:participants"
    
    # Redis에서 참가자 리스트를 가져옵니다.
        participants = redis_client.lrange(participants_key, 0, -1)

    # 각 참가자 정보를 JSON 형식으로 변환
        participants = [json.loads(p) for p in participants]

    # fingers가 0인 참가자를 찾습니다.
        loser = next((p for p in participants if p.get('fingers', 0) == 0), None)

    # 손가락 개수 기준으로 참가자 정렬 (내림차순)
        sorted_participants = sorted(participants, key=lambda p: p.get('fingers', 0), reverse=True)

    # 순위 정보 생성
        ranking = [
        {
            "rank": idx + 1,
            "userId": p["userId"],
            "nickname": p["nickname"],
            "fingers": p["fingers"]
        }
            for idx, p in enumerate(sorted_participants)
        ]

        if loser:
            print(f"Loser found: {loser}")  # 디버깅 출력
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "game_end",
                    "loser": {
                        "userId": loser['userId'],
                        "nickname": loser['nickname'],
                    "fingers": loser['fingers']
                },
                "ranking": ranking,
                "message": f"Game has ended! Loser is {loser['nickname']}."
            }
        )
            # # 게임 종료 처리
            # self.end_game()

        else:
            print("No loser found yet.")

    # def end_game(self):
    # # 게임이 끝났음을 나타내는 데이터 정리
    #     print(f"Ending game for room {self.room_id}")
    
    # # Redis에서 게임 참가자 목록 삭제
    #     participants_key = f"room:{self.room_id}:participants"
    #     redis_client.delete(participants_key)
    
    # # 추가적인 데이터 정리 작업 (예: 점수 기록, 기록 저장 등)
    #     self.cleanup_room()

    async def handle_fold(self, data):
        # HTTP 헤더에서 Cookie 가져오기
        headers = dict(self.scope["headers"])
        cookie_header = headers.get(b'cookie', b'').decode()

        # 쿠키 파싱
        cookies = SimpleCookie(cookie_header)
        user_id = cookies.get('user_id').value if 'user_id' in cookies else None

        if not user_id:
            await self.send(json.dumps({"type": "error", "message": "User ID not found in cookies."}, ensure_ascii=False))
            return

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
        # HTTP 헤더에서 Cookie 가져오기
        headers = dict(self.scope["headers"])
        cookie_header = headers.get(b'cookie', b'').decode()

        # 쿠키 파싱
        cookies = SimpleCookie(cookie_header)
        user_id = cookies.get('user_id').value if 'user_id' in cookies else None

        if not user_id:
            await self.send(json.dumps({"type": "error", "message": "User ID not found in cookies."}, ensure_ascii=False))
            return


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
    

    async def make_chat(self, data):
        # HTTP 헤더에서 Cookie 가져오기
        headers = dict(self.scope["headers"])
        cookie_header = headers.get(b'cookie', b'').decode()

        # 쿠키 파싱
        cookies = SimpleCookie(cookie_header)
        user_id = cookies.get('user_id').value if 'user_id' in cookies else None

        if not user_id:
            await self.send_error("User ID not found in cookies.")
            return

        message = data.get("message")
        timestamp = time.time()

        if not message:
            await self.send_error("Message cannot be empty.")
            return

        # 참가자 목록 가져오기
        participants = await self.get_participants()
        
        # 디버깅 출력
        print(f"Participants: {participants}")
        print(f"User ID from cookie: {user_id}")

        nickname = next((p['nickname'] for p in participants if p['userId'] == user_id), None)

        if not nickname:
            await self.send_error("Nickname not found for user.")
            return

        # Redis에 메시지 저장
        message_data = {
            "userId": user_id,
            "nickname": nickname,
            "message": message,
            "timestamp": timestamp,
        }
        redis_client.rpush(f"room:{self.room_id}:messages", json.dumps(message_data))

        # 그룹에 메시지 브로드캐스트
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "new_chat", "message_data": message_data}
        )

    # 메시지 목록 요청 처리
    async def chat_list(self):
        messages_key = f"room:{self.room_id}:messages"
        messages = redis_client.lrange(messages_key, 0, -1)

        # Redis에서 가져온 메시지 디코딩
        decoded_messages = [
            json.loads(message.decode("utf-8")) for message in messages
        ]

        # 클라이언트로 메시지 목록 전송
        await self.send(json.dumps({
            "type": "message_list",
            "messages": decoded_messages
        }, ensure_ascii=False))

    # 새로운 메시지 이벤트 처리
    async def new_chat(self, event):
        message_data = event["message_data"]
        await self.send(json.dumps({
            "type": "new_message",
            "message": message_data
        }, ensure_ascii=False))