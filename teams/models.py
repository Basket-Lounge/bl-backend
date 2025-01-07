import uuid
from django.db import models

# Create your models here.
class Language(models.Model):
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return self.name
    
class Team(models.Model):
    id = models.PositiveBigIntegerField(primary_key=True)
    symbol = models.CharField(max_length=10)

    def __str__(self):
        return self.symbol
    
class TeamName(models.Model):
    id = models.AutoField(primary_key=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)

    def __str__(self):
        return f'{self.team.symbol} - {self.language.name} - {self.name}'
    
    class Meta:
        unique_together = ['team', 'language']


class TeamLike(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    favorite = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        unique_together = ['team', 'user']
        constraints = [
            models.UniqueConstraint(
                fields=['user'], 
                condition=models.Q(favorite=True),
                name='unique_team_like'
            )
        ]


class PostStatus(models.Model):
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name
    
class PostStatusDisplayName(models.Model):
    id = models.SmallAutoField(primary_key=True)
    post_status = models.ForeignKey(PostStatus, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=128)

    def __str__(self):
        return f'{self.post_status.name} - {self.language.name}'
    
    class Meta:
        unique_together = ['post_status', 'language']


class Post(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    status = models.ForeignKey(PostStatus, on_delete=models.PROTECT)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    title = models.CharField(max_length=512)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.title} - {self.team.symbol}' 
    
class PostHide(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        unique_together = ['post', 'user']

class PostLike(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        unique_together = ['post', 'user']

class PostCommentStatus(models.Model):
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=128)

    @staticmethod
    def get_created_role():
        return PostCommentStatus.objects.get(name='created')
    
    @staticmethod
    def get_deleted_role():
        return PostCommentStatus.objects.get(name='deleted')

    def __str__(self):
        return self.name

class PostCommentStatusDisplayName(models.Model):
    id = models.SmallAutoField(primary_key=True)
    post_comment_status = models.ForeignKey(PostCommentStatus, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=128)

    def __str__(self):
        return f'{self.post_comment_status.name} - {self.language.name}'
    
    class Meta:
        unique_together = ['post_comment_status', 'language']

class PostComment(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    status = models.ForeignKey(PostCommentStatus, on_delete=models.PROTECT)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.id}'

class PostCommentHide(models.Model):
    '''This model is used to hide a post comment'''
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    post_comment = models.ForeignKey(PostComment, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        unique_together = ['post_comment', 'user']

class PostCommentLike(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    post_comment = models.ForeignKey(PostComment, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        unique_together = ['post_comment', 'user']

class PostCommentReplyStatus(models.Model):
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=128)

    @staticmethod
    def get_created_role():
        return PostCommentReplyStatus.objects.get(name='created')
    
    @staticmethod
    def get_deleted_role():
        return PostCommentReplyStatus.objects.get(name='deleted')

    def __str__(self):
        return self.name
    
class PostCommentReplyStatusDisplayName(models.Model):
    id = models.SmallAutoField(primary_key=True)
    post_comment_reply_status = models.ForeignKey(PostCommentReplyStatus, on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=128)

    def __str__(self):
        return f'{self.post_comment_reply_status.name} - {self.language.name}'
    
    class Meta:
        unique_together = ['post_comment_reply_status', 'language']

class PostCommentReply(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    status = models.ForeignKey(
        PostCommentReplyStatus, 
        on_delete=models.PROTECT,
        default=PostCommentReplyStatus.get_created_role
    )
    post_comment = models.ForeignKey(PostComment, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.id}'
    
class PostCommentReplyHide(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    post_comment_reply = models.ForeignKey(PostCommentReply, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.id}'
    
    class Meta:
        unique_together = ['post_comment_reply', 'user']
