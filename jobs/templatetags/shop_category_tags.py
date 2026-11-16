from django import template

from jobs.shop_categories import split_categories

register = template.Library()


@register.filter
def category_tags(value):
    return split_categories(value)
