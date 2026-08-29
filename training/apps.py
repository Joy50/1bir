from django.apps import AppConfig


class TrainingConfig(AppConfig):
    name = "training"
    verbose_name = "Training"

    def ready(self):
        from django.template.utils import get_app_template_dirs

        get_app_template_dirs.cache_clear()
