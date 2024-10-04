from django import forms
from django.contrib import admin

# Register your models here.
from .models import User

class UserCreationForm(forms.ModelForm):
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ('role', 'username', 'email', 'password')

    def clean_password(self):
        if not self.cleaned_data['password']:
            raise forms.ValidationError('The Password field must be set')
        
        if len(self.cleaned_data['password']) < 8:
            raise forms.ValidationError('The Password field must be at least 8 characters long')
        
        return self.cleaned_data['password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_unusable_password()
        if commit:
            user.save()

        return user

class UserChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('role', 'username', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()

        return user
    

class UserAdmin(admin.ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('role', 'username', 'email', 'experience', 'is_profile_visible', 'is_staff', 'is_superuser')
    list_filter = ('role', 'is_profile_visible')
    fieldsets = (
        (None, {'fields': ('role', 'username', 'email', 'experience', 'is_profile_visible', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('role', 'username', 'email', 'password1', 'password2'),
        }),
    )
    search_fields = ('username', 'email')
    ordering = ('role', 'username', 'email')
    filter_horizontal = ()

admin.site.register(User, UserAdmin)