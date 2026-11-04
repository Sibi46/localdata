from django.db import migrations


CATEGORIES = [
    ('neighbourhood',    '🏘️',  'Neighbourhood'),
    ('education',        '📚',  'Education'),
    ('sports',           '⚽',  'Sports'),
    ('arts-culture',     '🎨',  'Arts & Culture'),
    ('business',         '💼',  'Business'),
    ('health-wellness',  '🏥',  'Health & Wellness'),
    ('environment',      '🌿',  'Environment'),
    ('religion-faith',   '🕌',  'Religion & Faith'),
    ('technology',       '💻',  'Technology'),
    ('politics-civic',   '🗳️',  'Politics & Civic'),
    ('family',           '👨‍👩‍👧‍👦', 'Family'),
    ('pets',             '🐾',  'Pets'),
    ('food-cooking',     '🍳',  'Food & Cooking'),
    ('travel',           '✈️',  'Travel'),
    ('music',            '🎵',  'Music'),
    ('volunteering',     '🤝',  'Volunteering'),
    ('seniors',          '👴',  'Seniors'),
    ('youth',            '🧒',  'Youth'),
    ('women',            '👩',  'Women'),
    ('agriculture',      '🌾',  'Agriculture'),
]


def seed(apps, schema_editor):
    Category = apps.get_model('portal', 'Category')
    for slug, icon, name in CATEGORIES:
        Category.objects.get_or_create(slug=slug, defaults={'name': name, 'icon': icon})


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0011_add_flick_approved_by'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
