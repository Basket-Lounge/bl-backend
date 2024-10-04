import uuid
from django.db import models

# Create your models here.
class ReportType(models.Model):
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=256)
    description = models.CharField(max_length=1000)

    def __str__(self):
        return self.name

class Report(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    accuser = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='accuser')
    accused = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='accused')
    solved = models.BooleanField(default=False)
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
    
class InquiryStatus(models.Model):
    id = models.SmallAutoField(primary_key=True)
    name = models.CharField(max_length=128)
    description = models.CharField(max_length=1000)

    def __str__(self):
        return self.name
    
class Inquiry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.ForeignKey(InquiryType, on_delete=models.CASCADE)
    status = models.ForeignKey(InquiryStatus, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    title = models.CharField(max_length=512)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} inquired about {self.type}'

class InquiryMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} in {self.inquiry}'