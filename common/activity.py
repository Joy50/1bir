from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType


def _log(user, obj, action_flag, message):
    if user is None or not getattr(user, "is_authenticated", False):
        return
    LogEntry.objects.create(
        user_id=user.pk,
        content_type=ContentType.objects.get_for_model(obj, for_concrete_model=False),
        object_id=str(obj.pk),
        object_repr=str(obj)[:200],
        action_flag=action_flag,
        change_message=message,
    )


def log_addition(user, obj, message="Added."):
    _log(user, obj, ADDITION, message)


def log_change(user, obj, message="Changed."):
    _log(user, obj, CHANGE, message)


def log_deletion(user, obj, message="Deleted."):
    _log(user, obj, DELETION, message)
