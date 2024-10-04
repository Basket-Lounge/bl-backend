import uuid
from django.db import models

# Create your models here.
class GameChat(models.Model):
    id = models.PositiveBigIntegerField(primary_key=True)
    slow_mode = models.BooleanField(default=False)
    slow_mode_time = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f'Chat {self.id}'
    

class GameChatMessage(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    chat = models.ForeignKey(
        GameChat, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} in {self.chat}'
    

class GameChatMute(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    chat = models.ForeignKey(
        GameChat, 
        on_delete=models.CASCADE, 
        related_name='mutes'
    )
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} in {self.chat} muted'
    

class GameChatBan(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user}'

class GamePrediction(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE
    )
    game = models.ForeignKey(
        GameChat,
        on_delete=models.CASCADE
    )
    prediction = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} prediction for {self.game}'    
    
    class Meta:
        unique_together = ['user', 'game']

