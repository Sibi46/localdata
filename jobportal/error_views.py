"""Missing pages must not depend on account, ad or notification queries."""
from django.http import HttpResponseNotFound
from django.template.loader import render_to_string


def not_found(request, exception):
    # No request means no database-backed context processors. Do not echo the
    # requested URL or exception, which can contain attacker-controlled values.
    response = HttpResponseNotFound(render_to_string('errors/not_found.html'))
    response['X-Robots-Tag'] = 'noindex, follow'
    return response
