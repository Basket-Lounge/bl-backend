from celery import shared_task

from api.websocket import broadcast_message_to_centrifuge, send_message_to_centrifuge
from management.services.models_services import InquiryService, filter_and_fetch_inquiry
from management.services.serializers_services import send_inquiry_message_to_live_chat, send_inquiry_notification_to_all_channels_for_moderators, send_inquiry_notification_to_specific_moderator, send_inquiry_notification_to_user, send_partially_updated_inquiry_to_live_chat
from users.services.models_services import UserChatService
from users.services.serializers_services import UserChatSerializerService

import logging

logger = logging.getLogger(__name__)

@shared_task
def broadcast_inquiry_updates_for_new_message_to_all_parties(inquiry_id, message_id):
    message = InquiryService.get_inquiry_message(message_id)
    inquiry = filter_and_fetch_inquiry(id=inquiry_id)

    if not inquiry:
        return

    send_inquiry_message_to_live_chat(message, inquiry.id)
    send_inquiry_notification_to_user(inquiry)
    send_inquiry_notification_to_all_channels_for_moderators(inquiry)

    for moderator in inquiry.inquirymoderator_set.all():
        send_inquiry_notification_to_specific_moderator(
            inquiry,
            moderator.moderator.id,
        )


@shared_task
def broadcast_inquiry_updates_to_all_parties(inquiry_id):
    inquiry = filter_and_fetch_inquiry(id=inquiry_id)

    send_partially_updated_inquiry_to_live_chat(inquiry)
    send_inquiry_notification_to_user(inquiry)
    send_inquiry_notification_to_all_channels_for_moderators(inquiry)

    for moderator in inquiry.inquirymoderator_set.all():
        send_inquiry_notification_to_specific_moderator(
            inquiry,
            moderator.moderator.id,
        )


@shared_task
def broadcast_chat_updates_for_new_message_to_all_parties(
    chat_id: str,
    message_id: str,
    sender_user_id: int,
    recipient_user_id: int,
):
    message = UserChatService.get_chat_message(message_id)
    if not message:
        return

    message_serializer = UserChatSerializerService.serialize_message_for_chat(message)

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
        chat_serializer.data
    )
    if not resp_json:
        return

    chat_channel_name = f'users/chats/{chat_id}'
    send_message_to_centrifuge(
        chat_channel_name, 
        message_serializer.data
    )