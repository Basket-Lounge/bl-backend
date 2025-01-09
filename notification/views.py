from rest_framework import viewsets

from notification.services.models_services import NotificationService
from notification.services.serializers_services import NotificationSerializerService

from rest_framework.decorators import action
from rest_framework.response import Response


class NotificationViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['get'], url_path='types')
    def get_notification_types(self, request):
        """
        Get all notification types.

        Args:
            request (Request): The request object.

        Returns:
            Response: The response object containing the notification types.

        """
        notification_types = NotificationService.get_notification_template_types() 
        serializer = NotificationSerializerService.serialize_notification_template_types(notification_types)

        return Response(serializer.data)