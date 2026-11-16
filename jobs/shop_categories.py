"""Category suggestions shared by shop registration and profile editing."""
from django import forms
from django.db.models import Q


CATEGORIES = (
    'Food', 'Restaurant', 'Bakery', 'Cafe', 'Tea shop', 'Sweets & Snacks', 'Catering',
    'Groceries', 'Supermarket', 'Vegetables', 'Fruits', 'Meat & Fish', 'Milk & Dairy',
    'Clothing', 'Menswear', 'Womenswear', 'Kidswear', 'Sarees', 'Tailoring',
    'Footwear', 'Bags', 'Jewellery', 'Cosmetics', 'Beauty salon',
    'Electronics', 'Appliance', 'Mobiles', 'Mobile accessories', 'Computer store',
    'Furniture', 'Home essentials', 'Kitchenware', 'Electrical', 'Hardware',
    'Plumbing', 'Paints', 'Building materials', 'Stationery', 'Books', 'Toys',
    'Gifts', 'Sports goods', 'Watch shop', 'Optical shop', 'Medical store',
    'Auto parts', 'Vehicle service', 'Pet shop', 'Laundry', 'Printing',
    'Photography', 'Agriculture', 'Other',
)
FOOD_CATEGORIES = ('food', 'restaurant', 'bakery', 'cafe', 'catering', 'hotel',
                   'sweet', 'snack', 'juice', 'tea shop', 'coffee', 'tiffin',
                   'groceries', 'supermarket', 'vegetable', 'fruit', 'meat', 'fish', 'milk', 'dairy')


class ShopCategoryInput(forms.TextInput):
    template_name = 'shop/category_input.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['category_options'] = CATEGORIES
        context['widget']['attrs']['list'] = context['widget']['attrs'].get('id', name) + '-options'
        context['widget']['attrs']['data-category-value'] = ''
        return context


def split_categories(value):
    return [item.strip() for item in (value or '').replace('\n', ',').split(',') if item.strip()]


class ShopCategoriesField(forms.CharField):
    widget = ShopCategoryInput

    def clean(self, value):
        values = split_categories(super().clean(value))
        selected = []
        seen = set()
        suggested = {item.casefold(): item for item in CATEGORIES}
        for item in values:
            key = item.casefold()
            if key not in seen:
                selected.append(suggested.get(key, item))
                seen.add(key)
        if len(selected) > 5:
            raise forms.ValidationError('Choose up to 5 shop categories.')
        result = ', '.join(selected)
        if len(result) > 100:
            raise forms.ValidationError('Keep your category names within 100 characters in total.')
        return result


def food_category_query(field):
    query = Q(**{field + '__icontains': FOOD_CATEGORIES[0]})
    for category in FOOD_CATEGORIES[1:]:
        query |= Q(**{field + '__icontains': category})
    return query
