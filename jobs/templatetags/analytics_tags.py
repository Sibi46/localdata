from django import template
from jobs.analytics import page_name

register=template.Library()
register.filter('analytics_page_name',page_name)
