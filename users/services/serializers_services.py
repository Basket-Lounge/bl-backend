from datetime import datetime, timezone
from typing import List
from api.exceptions import BadRequestError
from api.websocket import broadcast_message_to_centrifuge, send_message_to_centrifuge
from management.models import (
    InquiryMessage, 
)
from management.serializers import (
    InquiryCommonMessageSerializer, 
    InquiryMessageCreateSerializer, 
    InquirySerializer
)
from users.models import Block, User, UserChat, UserChatParticipant, UserChatParticipantMessage

from django.db.models.manager import BaseManager

from users.serializers import (
    BlockSerializer,
    PostCommentSerializer, 
    UserChatParticipantMessageCreateSerializer, 
    UserChatParticipantMessageSerializer, 
    UserChatSerializer, 
    UserSerializer, 
    UserUpdateSerializer
)

from rest_framework.request import Request

from users.services.models_services import UserChatService

import logging

logger = logging.getLogger(__name__)


def send_update_to_all_parties_regarding_chat_message(
    chat_id: str,
    message_id: str
) -> None:
    """
    Send an update to all parties regarding a chat message.

    Args:
        - chat_id (str): The ID of the chat to send updates for.
        - message_id (str): The ID of the message to send updates for.

    Returns:
        - None
    """
    message = UserChatService.get_chat_message(message_id)
    if not message:
        return

    message_serializer = UserChatSerializerService.serialize_message_for_chat(message)

    chat_channel_name = f'users/chats/{chat_id}'
    send_message_to_centrifuge(
        chat_channel_name, 
        message_serializer.data
    )

def send_partially_updated_chat_to_live_chat(
    chat_id: str,
    sender_user_id: int,
    recipient_user_id: int,
) -> None:
    """
    Send a partially updated chat to the live chat. Note that this function does not send the entire chat log.

    Args:
        - chat_id (str): The ID of the chat to send updates for.
        - sender_user_id (int): The ID of the user that sent the message.
        - recipient_user_id (int): The ID of the user that received the message.
    
    Returns:
        - None
    """
    chat = UserChatService.get_chat_by_id(chat_id)
    if not chat:
        return

    chat_serializer = UserChatSerializerService.serialize_chat_for_update(chat)

    channel_names = [
        f'users/{sender_user_id}/chats/updates',
        f'users/{recipient_user_id}/chats/updates',
    ]

    resp_json = broadcast_message_to_centrifuge(
        channel_names,
        chat_serializer.data,
    )

    if not resp_json:
        logger.error('Failed to broadcast chat updates to all parties')

    resp_json = send_message_to_centrifuge(
        f'users/chats/{chat_id}',
        chat_serializer.data,
        type='chat_update'
    )

class UserSerializerService:
    @staticmethod
    def update_user(request, user):
        serializer = UserUpdateSerializer(
            user,
            data=request.data,
            partial=True
        )         
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return serializer

    @staticmethod
    def serialize_user(user: User) -> UserSerializer:
        """
        Serialize a user object with the fields that are allowed to be seen by the owner of the account.

        :param user: The user object to serialize.

        :return: The UserSerializer object. 
        """

        return UserSerializer(
            user,
            fields=(
                'id',
                'username', 
                'email', 
                'role_data',
                'level',
                'introduction', 
                'created_at',
                'is_profile_visible',
                'chat_blocked',
                'likes_count',
                'favorite_team',
                'login_notification_enabled'
            ),
            context={
                'team': {
                    'fields': ['id', 'symbol']
                },
            }
        )
    
    @staticmethod
    def serialize_another_user(user: User, requesting_user: User = None) -> UserSerializer:
        """
        Serialize a user object with the fields that are allowed to be seen by another user.

        :param user: The user object to serialize.
        :param requesting_user: The user that is requesting the data.

        :return: The UserSerializer object.
        """

        fields = [
            'id',
            'username',
            'role_data',
            'level',
            'introduction',
            'created_at',
            'is_profile_visible',
            'chat_blocked',
            'likes_count',
            'favorite_team',
        ]

        if requesting_user is not None and requesting_user.is_authenticated:
            fields.append('liked')

        return UserSerializer(
            user,
            fields=fields,
            context={
                'team': {
                    'fields': ['id', 'symbol']
                },
            }
        )
    
    @staticmethod
    def serialize_user_with_id_only(user):
        return UserSerializer(
            user,
            fields=['id', 'likes_count', 'liked']
        )
    
    @staticmethod
    def serialize_blocked_users(blocked_users: BaseManager[Block] | List[Block]) -> List[dict]:
        """
        Serialize a list of blocked users.

        Args:
            - blocked_users: The list of blocked users to serialize.
        
        Returns:
            - A list of dictionaries containing the serialized data.
        """
        serializer = BlockSerializer(
            blocked_users,
            many=True,
            fields=['blocked_user_data'],
            context={
                'blocked_user': {
                    'fields': ['id', 'username']
                }
            }
        )

        data = []
        for block in serializer.data:
            data.append(block['blocked_user_data'])

        return data

class UserChatSerializerService:
    @staticmethod
    def create_chat_message(request: Request, user_id: int) -> tuple[UserChatParticipantMessage, UserChat] | tuple[None, None]:
        """
        Create a message in a chat between the authenticated user and another user.

        Args:
            - request: The request object.
            - user_id: The id of the user to chat with.
        
        Returns:
            - A tuple containing the message and the chat object.
        """
        if type(user_id) != int:
            user_id = int(user_id)

        if not request.user.is_authenticated:
            return None, None

        chat = UserChat.objects.filter(
            userchatparticipant__user=request.user,
        ).filter(
            userchatparticipant__user__id=user_id,
            userchatparticipant__chat_blocked=False,
            userchatparticipant__user__chat_blocked=False,
        ).only('id').first()

        if not chat:
            return None, None
        
        participants = UserChatParticipant.objects.filter(chat=chat).select_related('user')
        sender_participant = None
        receiver_participant = None

        for participant in participants:
            if participant.user.id == request.user.id:
                sender_participant = participant
            elif participant.user.id == user_id:
                receiver_participant = participant

            if sender_participant and receiver_participant:
                break

        if not sender_participant or not receiver_participant:
            return None, None

        serializer = UserChatParticipantMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(
            sender=sender_participant,
            receiver=receiver_participant
        )
        chat.updated_at = datetime.now(timezone.utc)
        chat.save()

        return message, chat

    @staticmethod
    def serialize_chats(request, chats):
        return UserChatSerializer(
            chats,
            many=True,
            fields=['id', 'participants'],
            context={
                'userchatparticipant': {
                    'fields': [
                        'user_data', 
                        'last_message', 
                        'unread_messages_count'
                    ]
                },
                'userchatparticipantmessage_extra': {
                    'user_id': request.user.id
                },
                'user': {
                    'fields': ['id', 'username', 'favorite_team']
                },
                'team': {
                    'fields': ['id', 'symbol']
                }
            }
        )
    
    @staticmethod
    def serialize_chats_without_unread_count(chats):
        return UserChatSerializer(
            chats,
            many=True,
            fields=['id', 'participants'],
            context={
                'userchatparticipant': {
                    'fields': [
                        'user_data', 
                        'last_message', 
                    ]
                },
                'userchatparticipantmessage': {
                    'fields_exclude': ['sender_data', 'user_data']
                },
                'user': {
                    'fields': ['id', 'username']
                }
            }
        )

    @staticmethod
    def serialize_chat(chat: UserChat) -> UserChatSerializer:
        """
        Serialize a chat object with the fields that are allowed to be seen by the owner of the account.

        Args:
            - chat: The chat object to serialize.
        
        Returns:
            - The UserChatSerializer object.
        """
        return UserChatSerializer(
            chat,
            fields=[
                'id', 
                'participants', 
                'created_at', 
                'updated_at'
            ],
            context={
                'userchatparticipant': {
                    'fields': ['user_data']
                },
                'user': {
                    'fields': ['id', 'username', 'favorite_team']
                },
                'team': {
                    'fields': ['id', 'symbol']
                }
            }
        )
    
    @staticmethod
    def serialize_chat_with_entire_log(chat):
        return UserChatSerializer(
            chat,
            fields=[
                'id', 
                'participants', 
                'created_at', 
                'updated_at'
            ],
            context={
                'userchatparticipant': {
                    'fields': ['user_data', 'messages']
                },
                'userchatparticipantmessage': {
                    'fields_exclude': ['sender_data', 'user_data'],
                },
                'user': {
                    'fields': ['id', 'username']
                }
            }
        )


    @staticmethod
    def serialize_chat_for_update(chat : UserChat):
        return UserChatSerializer(
            chat,
            fields=['id', 'participants', 'created_at', 'updated_at'],
            context={
                'userchatparticipant': {
                    'fields': [
                        'user_data', 
                        'last_message', 
                        'unread_messages_count'
                    ]
                },
                'user': {
                    'fields': ['id', 'username', 'favorite_team']
                },
                'team': {
                    'fields': ['id', 'symbol']
                }
            }
        )

    @staticmethod
    def serialize_message_for_chat(message : UserChatParticipantMessage):
        return UserChatParticipantMessageSerializer(
            message,
            fields_exclude=['sender_data'],
            context={
                'user': {
                    'fields': ['id', 'username', 'favorite_team']
                },
                'team': {
                    'fields': ['id', 'symbol']
                }
            }
        )
    
    @staticmethod
    def serialize_messages_for_chat(messages: BaseManager[UserChatParticipantMessage] | list) -> UserChatParticipantMessageSerializer:
        return UserChatParticipantMessageSerializer(
            messages,
            many=True,
            fields_exclude=['sender_data'],
            context={
                'user': {
                    'fields': ['id', 'username', 'favorite_team']
                },
                'team': {
                    'fields': ['id', 'symbol']
                }
            }
        )
    

class InquirySerializerService:
    @staticmethod
    def create_inquiry_message(inquiry_id, data: dict[str, str]) -> InquiryMessage:
        if not inquiry_id:
            raise BadRequestError('Inquiry id is required.')
        
        if not "message" in data:
            raise BadRequestError('Message is required.')

        serializer = InquiryMessageCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.save(
            inquiry=inquiry_id
        )

    @staticmethod
    def serialize_inquiries(request, inquiries):
        return InquirySerializer(
            inquiries,
            many=True,
            context={
                'inquiry': {
                    'fields': ['id']
                },
                'inquirytypedisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'inquirymoderator': {
                    'fields': [
                        'moderator_data', 
                        'last_message',
                    ]
                },
                'moderator': {
                    'fields': ['id', 'username', 'favorite_team']
                },
                'user': {
                    'fields': ['id', 'username', 'favorite_team']
                },
                'team': {
                    'fields': ['id', 'symbol']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

    @staticmethod
    def serialize_inquiry(inquiry):
        return InquirySerializer(
            inquiry,
            fields_exclude=[
                'user_data', 
                'last_message', 
                'unread_messages_count'
            ],
            context={
                'inquirytypedisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'inquirymessage': {
                    'fields_exclude': ['inquiry_data', 'user_data']
                },
                'inquirymoderator': {
                    'fields': ['moderator_data', 'messages']
                },
                'moderator': {
                    'fields': ['id', 'username']
                },
                'inquirymoderatormessage': {
                    'fields_exclude': ['inquiry_moderator_data', 'user_data']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )
    
    @staticmethod
    def serialize_inquiry_for_update(inquiry):
        return InquirySerializer(
            inquiry,
            fields_exclude=[
                'user_data', 
            ],
            context={
                'user': {
                    'fields': ['id', 'username']
                },
                'inquirytypedisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'inquirymoderator': {
                    'fields': [
                        'moderator_data', 
                        'last_message', 
                    ]
                },
                'moderator': {
                    'fields': ['id', 'username']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )
    
    @staticmethod
    def serialize_inquiry_messages(messages) -> InquiryCommonMessageSerializer:
        return InquiryCommonMessageSerializer(
            messages,
            many=True,
        )
    
class PostCommentSerializerService:
    @staticmethod
    def serialize_comments(request, comments):
        return PostCommentSerializer(
            comments,
            fields_exclude=['liked'] if not request.user.is_authenticated else [],
            many=True,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'status': {
                    'fields': ('id', 'name')
                },
                'post': {
                    'fields': ('id', 'title', 'team_data', 'user_data')
                },
                'team': {
                    'fields': ('id', 'symbol')
                }
            }
        )
    
    @staticmethod
    def serialize_comments_without_liked(comments):
        return PostCommentSerializer(
            comments,
            fields_exclude=['liked'],
            many=True,
            context={
                'user': {
                    'fields': ('id', 'username')
                },
                'status': {
                    'fields': ('id', 'name')
                },
                'post': {
                    'fields': ('id', 'title', 'team_data', 'user_data')
                },
                'team': {
                    'fields': ('id', 'symbol')
                }
            }
        )