from django.apps import AppConfig


class EygarprofileConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'eygarprofile'
    verbose_name = 'Eygar Profile Management'

    def ready(self):
        import eygarprofile.signals
