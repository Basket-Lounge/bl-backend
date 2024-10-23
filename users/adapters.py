from django.conf import settings

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_connect_redirect_url(self, request, socialaccount):
        print('socialaccount', socialaccount)
        return '/admin/asdfasdf/'