import uuid
from django.contrib.auth.models import AbstractBaseUser
from django.db import models

from users.utils import generate_random_username

from .managers import UserManager


class Role(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=512)
    weight = models.IntegerField()

    def __str__(self):
        return self.name
    
    @staticmethod
    def get_regular_user_role():
        return Role.objects.get(name='user')
    
    @staticmethod
    def get_banned_user_role():
        return Role.objects.get(name='banned')

    @staticmethod 
    def get_deactivated_user_role():
        return Role.objects.get(name='deactivated')

    @staticmethod 
    def get_chat_moderator_role():
        return Role.objects.get(name='chat_moderator')
    
    @staticmethod
    def get_site_moderator_role():
        return Role.objects.get(name='site_moderator')
    
    @staticmethod
    def get_admin_role():
        return Role.objects.get(name='admin')


class User(AbstractBaseUser):
    role = models.ForeignKey(
        Role, 
        on_delete=models.PROTECT,
        default=Role.get_regular_user_role
    )
    username = models.CharField(
        max_length=128, 
        unique=True, 
        default=generate_random_username
    )
    email = models.EmailField(unique=True)
    experience = models.IntegerField(default=0)
    introduction = models.TextField(blank=True)
    chat_blocked = models.BooleanField(default=False)
    is_profile_visible = models.BooleanField(
        default=True,
        verbose_name='Profile visibility'
    ) 
    is_staff = models.BooleanField(
        default=False,
        verbose_name='Staff status'
    )
    is_superuser = models.BooleanField(
        default=False,
        verbose_name='Superuser status'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Registration date'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Last update'
    )

    def __str__(self):
        return self.username
    
    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    # @property
    # def is_staff(self):
    #     "Is the user a member of staff?"
    #     # Simplest possible answer: All admins are staff
    #     return self.is_staff

    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['role', 'email']

    objects = UserManager()

class UserLike(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    liked_user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='liked_user'
    )

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        unique_together = ['user', 'liked_user']

class Block(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    blocked_user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='blocked_user'
    )

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        unique_together = ['user', 'blocked_user']


class UserChat(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.id}'
    
class UserChatParticipant(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chat = models.ForeignKey(UserChat, on_delete=models.CASCADE)
    chat_deleted = models.BooleanField(default=False)
    last_deleted_at = models.DateTimeField(
        null=True, 
        help_text="Last time the user deleted the chat"
    )
    last_read_at = models.DateTimeField(
        auto_now=True, 
        help_text="Last time the other user read the chat"
    )
    chat_blocked = models.BooleanField(
        default=False, 
        help_text="Whether the user blocked the chat"
    )
    last_blocked_at = models.DateTimeField(null=True)

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        unique_together = ['user', 'chat']

class UserChatParticipantMessage(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    sender = models.ForeignKey(
        UserChatParticipant, 
        on_delete=models.CASCADE
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.id}'