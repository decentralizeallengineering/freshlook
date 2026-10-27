# label: duplicate
# sample: sought
# a: django/contrib/admin/options.py:944 log_addition
# b: django/contrib/admin/options.py:960 log_change
# why: Identical LogEntry.log_actions call differing only in the action flag constant (ADDITION vs CHANGE).
def log_addition(self, request, obj, message):
    """
    Log that an object has been successfully added.

    The default implementation creates an admin LogEntry object.
    """
    from django.contrib.admin.models import ADDITION, LogEntry

    return LogEntry.objects.log_actions(
        user_id=request.user.pk,
        queryset=[obj],
        action_flag=ADDITION,
        change_message=message,
        single_object=True,
    )


def log_change(self, request, obj, message):
    """
    Log that an object has been successfully changed.

    The default implementation creates an admin LogEntry object.
    """
    from django.contrib.admin.models import CHANGE, LogEntry

    return LogEntry.objects.log_actions(
        user_id=request.user.pk,
        queryset=[obj],
        action_flag=CHANGE,
        change_message=message,
        single_object=True,
    )
