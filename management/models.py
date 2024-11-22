import uuid
from django.db import models

# Create your models here.
class ReportType(models.Model):
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=256)
    description = models.CharField(max_length=1000)

    def __str__(self):
        return self.name


class ReportTypeDisplayName(models.Model):
    id = models.SmallAutoField(primary_key=True)
    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    language = models.ForeignKey('teams.Language', on_delete=models.CASCADE)
    display_name = models.CharField(max_length=256)

    def __str__(self):
        return self.display_name


class Report(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    accuser = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        related_name='accuser'
    )
    accused = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        related_name='accused'
    )
    resolved = models.BooleanField(default=False)
    title = models.CharField(max_length=512)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.accuser} reported {self.accused}'
    

class InquiryType(models.Model):
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=512)
    description = models.CharField(max_length=1000)

    def __str__(self):
        return self.name


class InquiryTypeDisplayName(models.Model):
    id = models.SmallAutoField(primary_key=True)
    inquiry_type = models.ForeignKey(InquiryType, on_delete=models.CASCADE)
    language = models.ForeignKey('teams.Language', on_delete=models.CASCADE)
    display_name = models.CharField(max_length=512)

    def __str__(self):
        return self.display_name
    
class Inquiry(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    inquiry_type = models.ForeignKey(InquiryType, on_delete=models.CASCADE)
    solved = models.BooleanField(default=False)
    last_read_at = models.DateTimeField(
        auto_now_add=True, 
        help_text='Last time the user read the inquiry',
    )
    title = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} inquired about {self.type}'
    
class InquiryModerator(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE)
    moderator = models.ForeignKey('users.User', on_delete=models.CASCADE)
    last_read_at = models.DateTimeField(
        auto_now_add=True, 
        help_text='Last time the moderator read the inquiry',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    in_charge = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.moderator} assigned to {self.inquiry}'
    
class InquiryModeratorMessage(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    inquiry_moderator = models.ForeignKey(InquiryModerator, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.moderator} in {self.inquiry}'

class InquiryMessage(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    inquiry = models.ForeignKey(
        Inquiry, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} in {self.inquiry}'