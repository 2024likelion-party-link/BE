from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Room, RoomParticipant
from .serializers import RoomSerializer, RoomParticipantSerializer


class CreateRoomView(APIView):
    """
    방 생성 API
    닉네임을 받아 방을 생성하고, 고유 URL을 생성합니다.
    """
    def post(self, request):
        nickname = request.data.get('nickname')  # 클라이언트가 전달한 닉네임

        if not nickname:
            return Response(
                {"error": "The 'nickname' field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 방 생성
        room = Room.objects.create(host=request.user)

        # 방 호스트를 참가자로 추가
        RoomParticipant.objects.create(room=room, user=request.user, nickname=nickname)

        # 고유 URL 생성
        room_url = request.build_absolute_uri(reverse('room-detail', kwargs={'room_code': room.room_code}))

        response_data = {
            "room": RoomSerializer(room).data,
            "room_url": room_url  # 클라이언트에게 URL 반환
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
    

class JoinRoomView(APIView):
    """
    방 참가 API
    닉네임과 방 ID를 받아 사용자를 해당 방에 추가합니다.
    """
    def post(self, request, room_id):
        nickname = request.data.get('nickname')

        if not nickname:
            return Response(
                {"error": "'nickname' field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 방 유효성 확인
        room = get_object_or_404(Room, id=room_id, is_active=True)

        # 참가자 생성
        participant = RoomParticipant.objects.create(room=room, user=request.user, nickname=nickname)

        return Response(RoomParticipantSerializer(participant).data, status=status.HTTP_201_CREATED)
