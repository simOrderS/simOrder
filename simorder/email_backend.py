from django.core.mail.backends.smtp import EmailBackend
from .models import SystemSettings

class DatabaseEmailBackend(EmailBackend):
    def __init__(self, **kwargs):
        config = SystemSettings.objects.first()
        params = {
            'host': config.emailHost,
            'port': 587,
            'username': config.emailUser,
            'password': config.emailPassword,
            'use_tls': True,
        }

        params.update(kwargs)
        super().__init__(**params)
