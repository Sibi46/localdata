"""Category suggestions shared by shop registration and profile editing."""
from django import forms
from django.db.models import Q


CATEGORIES = ('Food', 'Restaurant', 'Bakery', 'Cafe', 'Groceries', 'Clothing',
              'Jewellery', 'Electronics', 'Appliance', 'Stationery', 'Other')
FOOD_CATEGORIES = ('food', 'restaurant', 'bakery', 'cafe', 'catering', 'hotel',
                   'sweet', 'snack', 'juice', 'tea shop', 'coffee', 'tiffin')


class ShopCategoryInput(forms.TextInput):
    template_name = 'shop/category_input.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['category_options'] = CATEGORIES
        context['widget']['attrs']['list'] = context['widget']['attrs'].get('id', name) + '-options'
        return context


def food_category_query(field):
    query = Q(**{field + '__icontains': FOOD_CATEGORIES[0]})
    for category in FOOD_CATEGORIES[1:]:
        query |= Q(**{field + '__icontains': category})
    return query
