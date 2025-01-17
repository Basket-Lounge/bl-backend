from celery import shared_task

from management.services.models_services import InquiryService, filter_and_fetch_inquiry
from management.services.serializers_services import send_inquiry_message_to_live_chat, send_inquiry_notification_to_all_channels_for_moderators, send_inquiry_notification_to_specific_moderator, send_inquiry_notification_to_user, send_partially_updated_inquiry_to_live_chat


@shared_task
def broadcast_inquiry_updates_for_new_message_to_all_parties(inquiry_id, message_id):
    message = InquiryService.get_inquiry_message(message_id)
    inquiry = filter_and_fetch_inquiry(id=inquiry_id)

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