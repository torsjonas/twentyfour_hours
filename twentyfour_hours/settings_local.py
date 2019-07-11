DEBUG = True

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'twentyfour_hours_3',
        'USER': 'root',
        'PASSWORD': 'not2secret!ml',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    },
}
