from typing import Any
from django import forms

from teams.models import PostStatus


class TeamPostForm(forms.Form):
    status = forms.IntegerField()
    title = forms.CharField(max_length=128)
    content = forms.CharField(widget=forms.Textarea)

    def clean_status(self) -> PostStatus:
        status = self.cleaned_data['status']
        try:
            status_obj = PostStatus.objects.exclude(name='deleted').get(id=status)
        except PostStatus.DoesNotExist:
            raise forms.ValidationError('Invalid status')

        return status_obj
    
    def clean_title(self):
        title = self.cleaned_data['title']
        if len(title) < 5:
            raise forms.ValidationError('Title is too short')

        return title
    
    def clean_content(self):
        content = self.cleaned_data['content']
        if len(content) < 1:
            raise forms.ValidationError('Content is too short')

        return content

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        title = cleaned_data.get('title')
        content = cleaned_data.get('content')

        if status and title and content:
            return cleaned_data

        raise forms.ValidationError('Invalid data')
    

class TeamPostCommentForm(forms.Form):
    content = forms.CharField()

    def clean_content(self):
        content = self.cleaned_data['content']
        if len(content) < 1:
            raise forms.ValidationError('Content is too short')

        return content