from celery import shared_task

from management.services.models_services import (
    InquiryModeratorService,
    InquiryService, 
    filter_and_fetch_inquiry
)
from management.services.serializers_services import (
    send_inquiry_message_to_live_chat, 
    send_inquiry_notification_to_all_channels_for_moderators, 
    send_inquiry_notification_to_specific_moderator, 
    send_inquiry_notification_to_user,
    send_new_moderator_to_live_chat,
    send_partially_updated_inquiry_to_live_chat,
    send_unassigned_inquiry_to_live_chat
)

@shared_task
def broadcast_inquiry_updates_for_new_message_to_all_parties(inquiry_id, message_id):
    message = InquiryModeratorService.get_inquiry_moderator_message(message_id)
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
def broadcast_inquiry_moderator_assignment_to_all_parties(inquiry_id: str, user_id: int):
    """
    Broadcast inquiry moderator assignment to all parties via WebSockets.

    Args:
        - inquiry_id (str): The ID of the inquiry to broadcast the moderator assignment for.
        - user_id (int): The ID of the user who was assigned as a moderator.
    
    Returns:
        - None
    """
    inquiry = InquiryService.get_inquiry_without_messages(inquiry_id)
    if not inquiry:
        return
    
    send_new_moderator_to_live_chat(inquiry, user_id)

@shared_task
def broadcast_inquiry_moderator_unassignment_to_all_parties(inquiry_id: str, user_id: int):
    """
    Broadcast inquiry moderator unassignment to all parties via WebSockets.

    Args:
        - inquiry_id (str): The ID of the inquiry to broadcast the moderator unassignment for.
        - user_id (int): The ID of the user who was unassigned as a moderator.
    
    Returns:
        - None
    """
    inquiry = InquiryService.get_inquiry_without_messages(inquiry_id)
    if not inquiry:
        return
    
    send_unassigned_inquiry_to_live_chat(inquiry, user_id)

@shared_task
def broadcast_inquiry_updates_to_all_parties(inquiry_id: str):
    """
    Broadcast inquiry updates to all parties via WebSockets.

    Args:
        - inquiry_id (str): The ID of the inquiry to broadcast updates for.
    """
    inquiry = filter_and_fetch_inquiry(id=inquiry_id)

    send_partially_updated_inquiry_to_live_chat(inquiry)
    send_inquiry_notification_to_user(inquiry)
    send_inquiry_notification_to_all_channels_for_moderators(inquiry)

    for moderator in inquiry.inquirymoderator_set.all():
        send_inquiry_notification_to_specific_moderator(
            inquiry,
            moderator.moderator.id,
        )