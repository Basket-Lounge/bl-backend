from django.contrib.auth.base_user import BaseUserManager
import uuid

class UserManager(BaseUserManager):
    def create_user(self, username, email, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')

        user = self.model(
            username=username or str(uuid.uuid4()),
            email=email, 
            **extra_fields
        )
        user.set_unusable_password()
        user.save()

        return user
    
    def create_superuser(self, **extra_fields):
        raise NotImplementedError