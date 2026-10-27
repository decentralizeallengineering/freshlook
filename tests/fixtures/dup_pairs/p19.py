# label: duplicate
# sample: sought
# a: django/contrib/contenttypes/fields.py:162 get_prefetch_queryset
# b: django/contrib/contenttypes/fields.py:629 get_prefetch_queryset
# why: Exact copy of the deprecated get_prefetch_queryset shim in two classes of the same module.
def get_prefetch_queryset(self, instances, queryset=None):
    warnings.warn(
        "get_prefetch_queryset() is deprecated. Use get_prefetch_querysets() "
        "instead.",
        RemovedInDjango60Warning,
        stacklevel=2,
    )
    if queryset is None:
        return self.get_prefetch_querysets(instances)
    return self.get_prefetch_querysets(instances, [queryset])


def get_prefetch_queryset(self, instances, queryset=None):
    warnings.warn(
        "get_prefetch_queryset() is deprecated. Use get_prefetch_querysets() "
        "instead.",
        RemovedInDjango60Warning,
        stacklevel=2,
    )
    if queryset is None:
        return self.get_prefetch_querysets(instances)
    return self.get_prefetch_querysets(instances, [queryset])
