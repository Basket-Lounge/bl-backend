import uuid
from django.db import models

# Create your models here.
class NotificationTemplateType(models.Model):
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=512)

    def __str__(self):
        return self.name

class NotificationTemplate(models.Model):
    id = models.AutoField(primary_key=True)
    type = models.ForeignKey(NotificationTemplateType, on_delete=models.CASCADE)
    name = models.CharField(max_length=512)
    template = models.TextField()

    def __str__(self):
        return self.name
    
class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        ordering = ['-created_at']

class NotificationRecipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    read = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} received {self.notification}'
    
    class Meta:
        ordering = ['-created_at']