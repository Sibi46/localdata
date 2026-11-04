SECRET_KEY = 'your-secret-key-here'

ANTHROPIC_API_KEY = 'your-anthropic-api-key-here'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME':   'localjobs_db',
        'USER':   'root',
        'PASSWORD': 'your-db-password',
        'HOST':   'localhost',
        'PORT':   '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}
