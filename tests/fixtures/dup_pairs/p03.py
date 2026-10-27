# label: distinct
# sample: random
# a: django/contrib/admin/checks.py:524 _check_filter_item
# b: django/contrib/admin/checks.py:995 _check_list_filter_item
# why: Different checks: one validates a many-to-many filter field, the other validates three forms of list_filter entries.
def _check_filter_item(self, obj, field_name, label):
    """Check one item of `filter_vertical` or `filter_horizontal`, i.e.
    check that given field exists and is a ManyToManyField."""

    try:
        field = obj.model._meta.get_field(field_name)
    except FieldDoesNotExist:
        return refer_to_missing_field(
            field=field_name, option=label, obj=obj, id="admin.E019"
        )
    else:
        if not field.many_to_many or isinstance(field, models.ManyToManyRel):
            return must_be(
                "a many-to-many field", option=label, obj=obj, id="admin.E020"
            )
        elif not field.remote_field.through._meta.auto_created:
            return [
                checks.Error(
                    f"The value of '{label}' cannot include the ManyToManyField "
                    f"'{field_name}', because that field manually specifies a "
                    f"relationship model.",
                    obj=obj.__class__,
                    id="admin.E013",
                )
            ]
        else:
            return []


def _check_list_filter_item(self, obj, item, label):
    """
    Check one item of `list_filter`, i.e. check if it is one of three options:
    1. 'field' -- a basic field filter, possibly w/ relationships (e.g.
       'field__rel')
    2. ('field', SomeFieldListFilter) - a field-based list filter class
    3. SomeListFilter - a non-field list filter class
    """
    from django.contrib.admin import FieldListFilter, ListFilter

    if callable(item) and not isinstance(item, models.Field):
        # If item is option 3, it should be a ListFilter...
        if not _issubclass(item, ListFilter):
            return must_inherit_from(
                parent="ListFilter", option=label, obj=obj, id="admin.E113"
            )
        # ...  but not a FieldListFilter.
        elif issubclass(item, FieldListFilter):
            return [
                checks.Error(
                    "The value of '%s' must not inherit from 'FieldListFilter'."
                    % label,
                    obj=obj.__class__,
                    id="admin.E114",
                )
            ]
        else:
            return []
    elif isinstance(item, (tuple, list)):
        # item is option #2
        field, list_filter_class = item
        if not _issubclass(list_filter_class, FieldListFilter):
            return must_inherit_from(
                parent="FieldListFilter",
                option="%s[1]" % label,
                obj=obj,
                id="admin.E115",
            )
        else:
            return []
    else:
        # item is option #1
        field = item

        # Validate the field string
        try:
            get_fields_from_path(obj.model, field)
        except (NotRelationField, FieldDoesNotExist):
            return [
                checks.Error(
                    "The value of '%s' refers to '%s', which does not refer to a "
                    "Field." % (label, field),
                    obj=obj.__class__,
                    id="admin.E116",
                )
            ]
        else:
            return []
