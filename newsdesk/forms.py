from django import forms
from django.contrib.auth import get_user_model

from jobs.models import PinCode
from .models import Comment, NewsAgent, NewsItem, Rating
from .permissions import active_pincodes, is_admin


def pincode_input():
    return forms.TextInput(attrs={'inputmode': 'numeric', 'pattern': '[1-9][0-9]{5}',
                                  'maxlength': 6, 'placeholder': 'Enter 6-digit pincode',
                                  'autocomplete': 'postal-code'})


class FeedForm(forms.Form):
    pincode = forms.RegexField(regex=r'\A[1-9][0-9]{5}\Z', required=False,
                              widget=pincode_input(), error_messages={'invalid': 'Enter a valid 6-digit pincode.'})
    category = forms.ChoiceField(choices=[('', 'All categories')] + list(NewsItem.Category.choices), required=False)
    kind = forms.ChoiceField(choices=[('', 'News & events'), ('news', 'News'), ('event', 'Events')], required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class NewsItemForm(forms.ModelForm):
    class Meta:
        model = NewsItem
        fields = ['pincode', 'title', 'category', 'kind', 'body', 'photo', 'video', 'event_start', 'event_end', 'venue', 'status']
        widgets = {
            'body': forms.Textarea(attrs={'rows': 10}),
            'event_start': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'event_end': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
        }
        help_texts = {'photo': 'JPEG, PNG or WebP; up to 5 MB.', 'video': 'MP4 or WebM; up to 25 MB.', 'event_start': 'Local time (Asia/Kolkata). Required for events.', 'status': 'Drafts are visible only to your assigned desk and admins.'}

    def __init__(self, *args, user, pincode_as_code=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pincode'].queryset = active_pincodes()
        if pincode_as_code:
            self.fields['pincode'].to_field_name = 'code'
            self.fields['pincode'].widget = pincode_input()
            self.fields['pincode'].help_text = 'Enter any valid 6-digit pincode. New pincodes are added when you save.'
            self.fields['pincode'].error_messages['invalid_choice'] = 'Enter a registered, active pincode.'
            if self.instance.pk:
                self.initial['pincode'] = self.instance.pincode.code
        if not is_admin(user):
            self.fields.pop('pincode')
        # Never expose a direct storage URL, including for draft attachments.
        self.fields['photo'].widget = forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'})
        self.fields['video'].widget = forms.FileInput(attrs={'accept': 'video/mp4,video/webm'})


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {'text': forms.Textarea(attrs={'rows': 3, 'maxlength': 160, 'placeholder': 'Add something helpful to the conversation…'})}


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['stars']
        widgets = {'stars': forms.Select(choices=[(n, '★' * n) for n in range(1, 6)])}


class ReportForm(forms.Form):
    reason = forms.CharField(max_length=200, widget=forms.Textarea(attrs={'rows': 3}))


class AgentForm(forms.ModelForm):
    class Meta:
        model = NewsAgent
        fields = ['user', 'pincode', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = get_user_model().objects.filter(is_active=True).order_by('pk')
        self.fields['pincode'].queryset = PinCode.objects.select_related('district').order_by('code')


