import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from room.models import Room, Participant
from .models import HandGame, Hand
# c2c51c19-882e-44b5-bf8a-ba1ae272116a

class HandGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"handgame_{self.room_id}"

        # Room 및 HandGame 확인
        try:
            self.room = await sync_to_async(Room.objects.get)(room_id=self.room_id)
            self.game = await sync_to_async(HandGame.objects.get)(room=self.room)
        except Room.DoesNotExist:
            await self.close()
            return
        except HandGame.DoesNotExist:
            await self.close()
            return

        # WebSocket 연결
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # 그룹에서 제거
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        # WebSocket 메시지 처리
        data = json.loads(text_data)
        action = data.get("action")

        if action == "start_game":
            await self.start_game()
        elif action == "ask_question":
            await self.ask_question(data)
        elif action == "fold_finger":
            await self.fold_finger(data)
        elif action == "unfold_finger":
            await self.unfold_finger(data)

    async def start_game(self):
        participants = await sync_to_async(list)(self.room.participants.all())
        if len(participants) != 5:
            await self.send(json.dumps({"error": "5명의 참가자가 필요합니다."}))
            return

        # 모든 참가자에게 손가락 개수 초기화
        for participant in participants:
            hand, _ = await sync_to_async(Hand.objects.get_or_create)(participant=participant)
            hand.fingers = 5
            await sync_to_async(hand.save)()

        # 랜덤으로 순서 정하기
        from random import shuffle

        shuffle(participants)
        self.game.current_turn = participants[0]
        await sync_to_async(self.game.save)()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "game_state",
                "message": f"Game started! 첫 번째 플레이어: {self.game.current_turn.nickname}",
                "players": [{"nickname": p.nickname, "fingers": p.hand.fingers} for p in participants],
            },
        )

    async def ask_question(self, data):
        question = data.get("question")
        if not question:
            await self.send(json.dumps({"error": "질문이 비어 있습니다."}))
            return

        if self.game.current_turn.user_id != self.scope["cookies"].get("user_id"):
            await self.send(json.dumps({"error": "자신의 차례가 아닙니다."}))
            return

        # 질문 브로드캐스트
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "chat_message", "message": f"{self.game.current_turn.nickname}: {question}"}
        )

        # 15초 뒤 자동으로 다음 차례로 이동
        await self.next_turn()

    async def fold_finger(self, data):
        nickname = data.get("nickname")
        try:
            participant = await sync_to_async(Participant.objects.get)(
                room=self.room, nickname=nickname
            )
            hand = await sync_to_async(Hand.objects.get)(participant=participant)
        except Participant.DoesNotExist:
            await self.send(json.dumps({"error": "해당 참가자를 찾을 수 없습니다."}))
            return

        if hand.fingers > 0:
            hand.fingers -= 1
            await sync_to_async(hand.save)()

            # 손가락이 모두 접힌 경우
            if hand.fingers == 0:
                await self.end_game(participant)

            await self.update_game_state()

    async def unfold_finger(self, data):
        nickname = data.get("nickname")
        try:
            participant = await sync_to_async(Participant.objects.get)(
                room=self.room, nickname=nickname
            )
            hand = await sync_to_async(Hand.objects.get)(participant=participant)
        except Participant.DoesNotExist:
            await self.send(json.dumps({"error": "해당 참가자를 찾을 수 없습니다."}))
            return

        if hand.fingers < 5:
            hand.fingers += 1
            await sync_to_async(hand.save)()
            await self.update_game_state()

    async def next_turn(self):
        participants = await sync_to_async(list)(
            self.room.participants.filter(hand__fingers__gt=0)
        )
        current_index = participants.index(self.game.current_turn)
        next_index = (current_index + 1) % len(participants)

        self.game.current_turn = participants[next_index]
        await sync_to_async(self.game.save)()

        await self.update_game_state()

    async def update_game_state(self):
        players = await sync_to_async(list)(self.room.participants.all())
        game_state = {
            "type": "game_state",
            "players": [{"nickname": p.nickname, "fingers": p.hand.fingers} for p in players],
            "current_turn": self.game.current_turn.nickname,
        }
        await self.channel_layer.group_send(self.room_group_name, game_state)

    async def end_game(self, losing_player):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": f"{losing_player.nickname}님의 손가락이 모두 접혔습니다! 게임 종료.",
            },
        )
