# label: distinct
# sample: random
# a: django/contrib/auth/backends.py:27 has_perm
# b: django/contrib/auth/backends.py:111 has_module_perms
# why: Different checks: membership of a perm vs any perm prefixed by an app label (with is_active).
def has_perm(self, user_obj, perm, obj=None):
    return perm in self.get_all_permissions(user_obj, obj=obj)


def has_module_perms(self, user_obj, app_label):
    """
    Return True if user_obj has any permissions in the given app_label.
    """
    return user_obj.is_active and any(
        perm[: perm.index(".")] == app_label
        for perm in self.get_all_permissions(user_obj)
    )
