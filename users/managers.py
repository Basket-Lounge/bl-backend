from django.contrib.auth.base_user import BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, role, username, email, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')

        user = self.model(
            role=role, 
            username=username,
            email=email, 
            **extra_fields
        )
        user.set_unusable_password()
        user.save()

        return user
    
    def create_superuser(self, **extra_fields):
        raise NotImplementedError