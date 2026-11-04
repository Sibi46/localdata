import re

from django import forms

from .identity_uploads import validate_identity, validate_profile_photo
from .models import NewsItem
from .permissions import active_pincodes


def clean_story(value):
    value = value.replace('\u200b', '').replace('\ufeff', '').strip()
    if not value:
        raise forms.ValidationError('Enter your news text.')
    if len(re.findall(r'\S+', value)) > 200:
        raise forms.ValidationError('Keep your news within 200 words.')
    return value


class ShareNewsForm(forms.Form):
    token = forms.UUIDField(widget=forms.HiddenInput)
    name = forms.CharField(max_length=120, label='Your full name')
    pincode = forms.RegexField(r'\A[1-9][0-9]{5}\Z', label='PIN code', widget=forms.TextInput(attrs={'inputmode': 'numeric', 'maxlength': 6}))
    address = forms.CharField(max_length=1000, widget=forms.Textarea(attrs={'rows': 3}))
    aadhaar = forms.FileField(label='Aadhaar card', validators=[validate_identity], help_text='PDF, JPEG, PNG or WebP, up to 5 MB. A masked Aadhaar is accepted. Only authorised editors can review this document.')
    profile_photo = forms.FileField(validators=[validate_profile_photo], help_text='JPEG, PNG or WebP, up to 5 MB. Used for editorial identity review, not published with your news.')
    topic = forms.CharField(max_length=180, label='News topic / headline')
    body = forms.CharField(max_length=12000, label='Your news (up to 200 words)', widget=forms.Textarea(attrs={'rows': 7, 'data-news-body': ''}))
    terms = forms.BooleanField(label='I have read and accept the news-sharing terms below.')
    accuracy = forms.BooleanField(label='I confirm that this news is accurate to the best of my knowledge and is not fabricated, misleading or copied without permission.')

    def __init__(self, *args, contributor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.contributor = contributor
        if contributor:
            for name in ('name', 'pincode', 'address', 'aadhaar', 'profile_photo'):
                self.fields.pop(name)

    def clean_pincode(self):
        pin = active_pincodes().filter(code=self.cleaned_data['pincode']).first()
        if not pin:
            raise forms.ValidationError('Enter an active six-digit PIN code supported by News Desk.')
        return pin

    def clean_body(self):
        return clean_story(self.cleaned_data['body'])


class ReviewSubmissionForm(forms.Form):
    topic = forms.CharField(max_length=180, label='Published headline')
    body = forms.CharField(max_length=12000, widget=forms.Textarea(attrs={'rows': 8}), label='News text (up to 200 words)')
    category = forms.ChoiceField(choices=NewsItem.Category.choices)
    decision = forms.ChoiceField(choices=[('publish', 'Approve and publish'), ('reject', 'Reject submission')])
    identity_checked = forms.BooleanField(required=False, label='I reviewed the submitted identity document and profile information.')
    note = forms.CharField(max_length=2000, required=False, widget=forms.Textarea(attrs={'rows': 3}), label='Editor note (shared with contributor)')

    def clean_body(self):
        return clean_story(self.cleaned_data['body'])

    def clean(self):
        data = super().clean()
        if data.get('decision') == 'publish' and not data.get('identity_checked'):
            self.add_error('identity_checked', 'Review the identity document before publishing.')
        if data.get('decision') == 'reject' and not data.get('note', '').strip():
            self.add_error('note', 'Explain why the submission was not approved.')
        return data
