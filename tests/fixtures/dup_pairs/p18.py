# label: distinct
# sample: random
# a: django/contrib/admin/models.py:134 Meta
# b: django/contrib/auth/models.py:126 Meta
# why: Model Meta declarations with different options and values; declarative, nothing to merge.
class Meta:
    verbose_name = _("log entry")
    verbose_name_plural = _("log entries")
    db_table = "django_admin_log"
    ordering = ["-action_time"]


class Meta:
    verbose_name = _("group")
    verbose_name_plural = _("groups")
