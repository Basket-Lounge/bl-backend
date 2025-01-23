from celery import shared_task

from management.services.models_services import InquiryService, filter_and_fetch_inquiry
from management.services.serializers_services import (
    send_inquiry_message_to_live_chat, 
    send_inquiry_notification_to_all_channels_for_moderators, 
    send_inquiry_notification_to_specific_moderator, 
    send_inquiry_notification_to_user, 
    send_partially_updated_inquiry_to_live_chat
)
from users.services.serializers_services import (
    send_partially_updated_chat_to_live_chat, 
    send_update_to_all_parties_regarding_chat_message
)

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
    send_partially_updated_chat_to_live_chat(chat_id, sender_user_id, recipient_user_id)
    send_update_to_all_parties_regarding_chat_message(chat_id, message_id)