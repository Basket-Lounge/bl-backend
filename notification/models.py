import uuid
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()

class NotificationTemplateType(models.Model):
    name = models.CharField(max_length=512, unique=True)
    description = models.CharField(max_length=2048)
    color_code = models.CharField(max_length=7, default='#423F3E')

    def __str__(self):
        return f'{self.name} ({self.id})'
    
class NotificationTemplateTypeDisplayName(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    type = models.ForeignKey(NotificationTemplateType, on_delete=models.CASCADE)
    language = models.ForeignKey('teams.Language', on_delete=models.PROTECT)
    name = models.CharField(max_length=512)

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        unique_together = ['type', 'language']
    
class NotificationTemplate(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    type = models.ForeignKey(NotificationTemplateType, on_delete=models.CASCADE)
    picture_url_template = models.CharField(blank=True, null=True, max_length=1024)
    redirect_url_template = models.CharField(blank=True, null=True, max_length=1024)
    subject = models.CharField(max_length=512)

    def __str__(self):
        return f'{self.id}'
    
class NotificationTemplateBody(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    template = models.ForeignKey(NotificationTemplate, on_delete=models.PROTECT)
    language = models.ForeignKey('teams.Language', on_delete=models.PROTECT)
    body = models.TextField()

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        unique_together = ['template', 'language']

class NotificationActor(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    notification = models.ForeignKey('Notification', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    post = models.ForeignKey('teams.Post', on_delete=models.CASCADE, blank=True, null=True)
    comment = models.ForeignKey('teams.PostComment', on_delete=models.CASCADE, blank=True, null=True)
    reply = models.ForeignKey('teams.PostCommentReply', on_delete=models.CASCADE, blank=True, null=True)
    game = models.ForeignKey('games.Game', on_delete=models.CASCADE, blank=True, null=True)
    player = models.ForeignKey('players.Player', on_delete=models.CASCADE, blank=True, null=True)
    team = models.ForeignKey('teams.Team', on_delete=models.CASCADE, blank=True, null=True)
    chat = models.ForeignKey('users.UserChat', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        unique_together = [
            ['notification', 'user'],
            ['notification', 'post'],
            ['notification', 'comment'],
            ['notification', 'reply'],
            ['notification', 'game'],
            ['notification', 'player'],
            ['notification', 'team'],
            ['notification', 'chat']
        ]
    
class Notification(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE)
    data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.id}'
    
class NotificationRecipient(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True)
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        unique_together = ['notification', 'recipient']