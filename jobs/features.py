"""Public feature destinations used by homepage discovery and search."""
FEATURES = [
    {'name': 'Products', 'url': '/products/', 'keywords': 'shopping product item price discount shop'},
    {'name': 'Shops and businesses', 'url': '/businesses/', 'keywords': 'store shopping local company directory'},
    {'name': 'Offers', 'url': '/advertise/', 'keywords': 'deals discounts sale advertisement'},
    {'name': 'Local News', 'url': '/news/', 'keywords': 'news local updates headlines'},
    {'name': 'Flicks', 'url': '/flicks/', 'keywords': 'video reels films watch'},
    {'name': 'Advertise your business', 'url': '/advertise/register/', 'keywords': 'promote marketing ads campaign'},
    {'name': 'Messages', 'url': '/messages/', 'keywords': 'chat conversations inbox'},
    {'name': 'Register Business', 'url': '/register/?type=company', 'keywords': 'join company shop registration'},
    {'name': 'My Profile', 'url': '/profile/edit/', 'keywords': 'account photo personal settings'},
]


def search_features(query):
    words = query.casefold().split()
    return [item for item in FEATURES if all(
        word in (item['name'] + ' ' + item['keywords']).casefold() for word in words
    )] if words else []
