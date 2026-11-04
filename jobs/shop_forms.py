"""Owner-managed catalog and shop media forms."""
from decimal import Decimal
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import LocalOffer, Product, ShopVideo

IMAGE_TYPES = {'JPEG', 'PNG', 'WEBP'}


def check_image(image):
    if image:
        if image.size > 5 * 1024 * 1024:
            raise ValidationError('Choose an image smaller than 5 MB.')
        if hasattr(image, 'image') and image.image.format not in IMAGE_TYPES:
            raise ValidationError('Choose a JPG, PNG, or WebP image.')
    return image


class ProductImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ProductImagesField(forms.ImageField):
    widget = ProductImageInput(attrs={'accept': 'image/jpeg,image/png,image/webp', 'data-image-preview': 'product-upload-preview', 'data-max-images': '6', 'data-image-crop': 'product'})

    def clean(self, data, initial=None):
        if not data:
            return []
        images = data if isinstance(data, (list, tuple)) else [data]
        if len(images) > 6:
            raise ValidationError('Choose a maximum of 6 product images.')
        return [check_image(super(ProductImagesField, self).clean(image)) for image in images]


class ProductForm(forms.ModelForm):
    images = ProductImagesField(label='Product images (up to 6)', required=False,
                               help_text='Choose 1–6 JPG, PNG, or WebP images, up to 5 MB each. The first image is your cover. Choosing new images replaces the current gallery.')
    price = forms.DecimalField(label='Regular price (₹)', min_value=Decimal('0.01'), max_digits=12, decimal_places=2,
                               help_text='Your price before any discount.', widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': '499.00'}))
    discount_percent = forms.IntegerField(label='Discount (%)', min_value=0, max_value=100, required=False,
                                         help_text='Leave blank or enter 0 for the regular price.')

    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'image', 'price', 'discount_percent', 'is_active']
        labels = {'is_active': 'Show this product in my shop', 'image': 'Product image'}
        widgets = {'description': forms.Textarea(attrs={'rows': 4}), 'image': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'})}
        help_texts = {'image': 'JPG, PNG, or WebP. Up to 5 MB.', 'category': 'For example: clothing, groceries, or electronics.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].required = False
        self.order_fields(['name', 'category', 'description', 'images', 'image', 'price', 'discount_percent', 'is_active'])

    def clean(self):
        data = super().clean()
        if not data.get('images') and not data.get('image') and not self.instance.image:
            self.add_error('images', 'Choose at least one product image.')
        return data

    def clean_discount_percent(self):
        return self.cleaned_data.get('discount_percent') or 0

    def clean_image(self):
        return check_image(self.cleaned_data.get('image'))


class ShopVideoForm(forms.ModelForm):
    class Meta:
        model = ShopVideo
        fields = ['title', 'description', 'video', 'thumbnail', 'is_published']
        labels = {'is_published': 'Show this video on my shop page', 'thumbnail': 'Cover image (optional)'}
        widgets = {'description': forms.Textarea(attrs={'rows': 3}), 'video': forms.ClearableFileInput(attrs={'accept': 'video/mp4,video/webm'}),
                   'thumbnail': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'})}
        help_texts = {'video': 'MP4 or WebM, up to 50 MB.', 'thumbnail': 'JPG, PNG, or WebP, up to 5 MB.'}

    def clean_thumbnail(self):
        return check_image(self.cleaned_data.get('thumbnail'))

    def clean_video(self):
        video = self.cleaned_data.get('video')
        if video and hasattr(video, 'content_type'):
            if video.size > 50 * 1024 * 1024:
                raise ValidationError('Choose a video smaller than 50 MB.')
            extension = Path(video.name).suffix.lower()
            header = video.read(12)
            video.seek(0)
            valid = (extension == '.mp4' and header[4:8] == b'ftyp') or (extension == '.webm' and header[:4] == b'\x1aE\xdf\xa3')
            if not valid:
                raise ValidationError('Choose a valid MP4 or WebM video.')
        return video


class ShopOfferForm(forms.ModelForm):
    class Meta:
        model = LocalOffer
        fields = ['title', 'discount_text', 'category', 'description', 'image', 'valid_until', 'contact_phone']
        labels = {'discount_text': 'Offer / discount', 'valid_until': 'Valid until (optional)', 'image': 'Offer image (optional)'}
        widgets = {'description': forms.Textarea(attrs={'rows': 4}), 'valid_until': forms.DateInput(attrs={'type': 'date'}),
                   'image': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'})}
        help_texts = {'discount_text': 'For example: 20% off, buy one get one, or free delivery.'}

    def clean_image(self):
        return check_image(self.cleaned_data.get('image'))

    def clean_valid_until(self):
        date = self.cleaned_data.get('valid_until')
        if date and date < timezone.localdate():
            raise ValidationError('Choose today or a future date.')
        return date

    def clean_contact_phone(self):
        phone = self.cleaned_data.get('contact_phone', '').strip()
        if phone and (not phone.isascii() or not phone.isdigit() or len(phone) != 10):
            raise ValidationError('Enter a 10-digit mobile number.')
        return phone


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleImageInput(attrs={'accept': 'image/jpeg,image/png,image/webp'})

    def clean(self, data, initial=None):
        if not data:
            raise ValidationError('Choose at least one image.')
        images = data if isinstance(data, (list, tuple)) else [data]
        if len(images) > 10:
            raise ValidationError('Upload up to 10 images at a time.')
        return [check_image(super(MultipleImageField, self).clean(image, initial)) for image in images]


class ShopPhotosForm(forms.Form):
    gallery_images = MultipleImageField(label='Shop photos', help_text='Up to 10 JPG, PNG, or WebP images. Maximum 5 MB each.')
    caption = forms.CharField(max_length=200, required=False)
