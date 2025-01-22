from datetime import datetime, timezone
from api.exceptions import BadRequestError
from api.websocket import send_message_to_centrifuge
from management.models import (
    Inquiry, 
    InquiryMessage, 
)
from management.serializers import (
    InquiryCommonMessageSerializer, 
    InquiryMessageCreateSerializer, 
    InquirySerializer
)
from users.models import User, UserChat, UserChatParticipant, UserChatParticipantMessage

from django.db.models.manager import BaseManager

from users.serializers import (
    PostCommentSerializer, 
    UserChatParticipantMessageCreateSerializer, 
    UserChatParticipantMessageSerializer, 
    UserChatSerializer, 
    UserSerializer, 
    UserUpdateSerializer
)

from rest_framework.request import Request


def send_update_to_all_parties_regarding_chat(
    sender_user_id: int,
    recipient_user_id: int,
    chat_id: str,
    chat_serializer,
    message_serializer
):
    sender_chat_notification_channel_name = f'users/{sender_user_id}/chats/updates'
    send_message_to_centrifuge(
        sender_chat_notification_channel_name,
        chat_serializer.data
    )

    recipient_chat_notification_channel_name = f'users/{recipient_user_id}/chats/updates'
    send_message_to_centrifuge(
        recipient_chat_notification_channel_name,
        chat_serializer.data
    ) 

    chat_channel_name = f'users/chats/{chat_id}'
    send_message_to_centrifuge(
        chat_channel_name, 
        message_serializer.data
    )


def send_update_to_all_parties_regarding_inquiry(
    inquiry: Inquiry,
    user: User,
    message_serializer,
    inquiry_update_serializer: InquirySerializer
):
    inquiry_channel_name = f'users/inquiries/{inquiry.id}'
    send_message_to_centrifuge(
        inquiry_channel_name,
        message_serializer.data
    )

    user_inquiry_notification_channel_name = f'users/{user.id}/inquiries/updates'
    send_message_to_centrifuge(
        user_inquiry_notification_channel_name,
        inquiry_update_serializer.data
    )

    ## TODO: Fix this to reflect the changes in both the queryset and the serializer 
    for moderator in inquiry.inquirymoderator_set.all():
        moderator_inquiry_notification_channel_name = f'moderators/{moderator.moderator.id}/inquiries/updates'

        inquiry_for_moderators_serializer = InquirySerializer(
            inquiry,
            fields_exclude=['user_data', 'unread_messages_count'],
            context={
                'user': {
                    'fields': ['id', 'username']
                },
                'inquirytypedisplayname': {
                    'fields': ['display_name', 'language_data']
                },
                'inquirymoderator': {
                    'fields': ['moderator_data', 'last_message']
                },
                'moderator': {
                    'fields': ['id', 'username']
                },
                'language': {
                    'fields': ['name']
                }
            }
        )

        send_message_to_centrifuge(
            moderator_inquiry_notification_channel_name,
            inquiry_for_moderators_serializer.data
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