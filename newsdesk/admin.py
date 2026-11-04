from django.contrib import admin
from django.utils import timezone

from .forms import NewsItemForm
from .models import Comment, CommentReport, NewsAgent, NewsItem, Rating
from .permissions import is_admin


class DeskAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return is_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_admin(request.user)

    def has_add_permission(self, request):
        return is_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_admin(request.user)


@admin.register(NewsAgent)
class NewsAgentAdmin(DeskAdmin):
    list_display = ['user', 'pincode', 'is_active']
    list_filter = ['is_active', 'pincode']
    search_fields = ['user__first_name', 'user__username', 'pincode__code']
    autocomplete_fields = ['user']


@admin.register(NewsItem)
class NewsItemAdmin(DeskAdmin):
    list_display = ['title', 'pincode', 'kind', 'category', 'status', 'published_at']
    list_filter = ['status', 'kind', 'category', 'pincode']
    search_fields = ['title', 'body', 'pincode__code']
    readonly_fields = ['author', 'published_at', 'created_at', 'updated_at']
    form = NewsItemForm

    def get_form(self, request, obj=None, **kwargs):
        class RequestForm(NewsItemForm):
            def __init__(self, *args, **form_kwargs):
                form_kwargs['user'] = request.user
                super().__init__(*args, **form_kwargs)
                if obj and 'pincode' in self.fields:
                    self.fields['pincode'].disabled = True
        kwargs['form'] = RequestForm
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        obj.save()


class ReadOnlySubmissionAdmin(DeskAdmin):
    def has_add_permission(self, request):
        return False


@admin.register(Comment)
class CommentAdmin(ReadOnlySubmissionAdmin):
    list_display = ['item', 'user', 'text', 'is_hidden', 'created_at']
    list_filter = ['is_hidden', 'item__pincode']
    search_fields = ['text', 'item__title']
    readonly_fields = ['item', 'user', 'text', 'created_at', 'moderated_by', 'moderated_at']

    def save_model(self, request, obj, form, change):
        obj.moderated_by = request.user
        obj.moderated_at = timezone.now()
        obj.save()
        if obj.is_hidden:
            obj.reports.update(resolved=True)


@admin.register(CommentReport)
class CommentReportAdmin(ReadOnlySubmissionAdmin):
    list_display = ['comment', 'reason', 'resolved', 'created_at']
    list_filter = ['resolved', 'comment__item__pincode']
    readonly_fields = ['comment', 'reporter', 'reason', 'created_at']


@admin.register(Rating)
class RatingAdmin(ReadOnlySubmissionAdmin):
    list_display = ['item', 'user', 'stars']
    readonly_fields = ['item', 'user', 'stars']


