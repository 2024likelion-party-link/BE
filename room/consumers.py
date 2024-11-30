import json
import random
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import redis
from django.conf import settings
from .models import Room, RoomParticipant

REDIS_CONN = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """사용자가 WebSocket에 연결될 때 실행."""
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"room_{self.room_id}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Broadcast updated participant list
        await self.update_participants_list()

    async def disconnect(self, close_code):
        """WebSocket 연결이 끊길 때 실행."""
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """WebSocket으로 메시지를 받았을 때 실행."""
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'join':
            await self.handle_join(data)
        elif action == 'propose_game':
            await self.handle_game_proposal(data)
        elif action == 'vote':
            await self.handle_vote(data)

    async def handle_join(self, data):
        """참가자가 방에 입장했을 때 처리."""
        nickname = data.get('nickname')
        user_id = self.scope['user'].id
        await self.add_participant(user_id, nickname)

        # Broadcast updated participant list
        await self.update_participants_list()

    async def handle_game_proposal(self, data):
        """게임 제안 처리."""
        proposer = data.get('proposer')  # 닉네임
        games = data.get('games', ['game1', 'game2'])
        redis_key = f"room_{self.room_id}_game_proposal"

        # 제안을 이미 존재하면 무시
        if REDIS_CONN.exists(redis_key):
            return

        # 가장 먼저 도달한 요청만 반영
        selected_game = random.choice(games) if len(games) == 2 else games[0]
        REDIS_CONN.set(redis_key, selected_game, ex=60)  # 1분간 제안 유효
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_proposed',
                'proposer': proposer,
                'selected_game': selected_game
            }
        )

    async def handle_vote(self, data):
        """게임 수락/거절 투표 처리."""
        vote = data.get('vote')  # "accept" 또는 "reject"
        user_id = self.scope['user'].id
        redis_key = f"room_{self.room_id}_votes"
        REDIS_CONN.hset(redis_key, user_id, vote)

        # 집계 확인
        votes = REDIS_CONN.hgetall(redis_key)
        accept_count = sum(1 for v in votes.values() if v == b'accept')
        reject_count = sum(1 for v in votes.values() if v == b'reject')

        # 투표 결과에 따라 처리
        if accept_count >= 2:
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'game_start'}
            )
            REDIS_CONN.delete(redis_key)  # 투표 초기화
        elif reject_count >= 2:
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'game_rejected'}
            )
            REDIS_CONN.delete(redis_key)  # 투표 초기화

    async def update_participants_list(self):
        """참가자 목록을 방의 다른 모든 사용자에게 방송."""
        participants = await self.get_participants()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'update_participants',
                'participants': participants
            }
        )

    async def game_proposed(self, event):
        """게임 제안 이벤트 방송."""
        await self.send(text_data=json.dumps({
            'action': 'game_proposed',
            'proposer': event['proposer'],
            'selected_game': event['selected_game']
        }))

    async def game_start(self, event):
        """게임 시작 이벤트 방송."""
        await self.send(text_data=json.dumps({'action': 'game_start'}))

    async def game_rejected(self, event):
        """게임 거절 이벤트 방송."""
        await self.send(text_data=json.dumps({'action': 'game_rejected'}))

    async def update_participants(self, event):
        """참가자 목록 업데이트."""
        participants = event['participants']
        await self.send(text_data=json.dumps({
            'action': 'update',
            'participants': participants
        }))

    @sync_to_async
    def add_participant(self, user_id, nickname):
        """DB에 참가자 추가."""
        user = User.objects.get(id=user_id)
        room = Room.objects.get(id=self.room_id)
        RoomParticipant.objects.create(room=room, user=user, nickname=nickname)

    @sync_to_async
    def get_participants(self):
        """방의 모든 참가자를 가져옴."""
        participants = RoomParticipant.objects.filter(room_id=self.room_id).values('nickname')
        return list(participants)
