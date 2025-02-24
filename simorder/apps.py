from django.apps import AppConfig


class simOrderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'simorder'
    verbose_name = 'MasterData' # so that is correctly displayed in the UI for Admin-Menu
