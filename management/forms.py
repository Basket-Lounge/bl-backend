from django import forms

from management.models import InquiryType


class InquiryForm(forms.Form):
    message = forms.CharField(max_length=4096)
    type = forms.IntegerField()

    def clean_message(self):
        message = self.cleaned_data['message']
        if len(message) < 1:
            raise forms.ValidationError('Message is too short')

        return message
    
    def clean_type(self):
        inquiry_type = self.cleaned_data['type']

        type_exists = InquiryType.objects.filter(id=inquiry_type).exists()
        if not type_exists:
            raise forms.ValidationError('Invalid type')

        return inquiry_type