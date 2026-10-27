# label: distinct
# sample: random
# a: django/contrib/admin/checks.py:351 _check_fieldsets
# b: django/contrib/admin/checks.py:372 _check_fieldsets_item
# why: Caller/callee pair: one iterates fieldsets, the other validates a single fieldset item structure.
def _check_fieldsets(self, obj):
    """Check that fieldsets is properly formatted and doesn't contain
    duplicates."""

    if obj.fieldsets is None:
        return []
    elif not isinstance(obj.fieldsets, (list, tuple)):
        return must_be(
            "a list or tuple", option="fieldsets", obj=obj, id="admin.E007"
        )
    else:
        seen_fields = []
        return list(
            chain.from_iterable(
                self._check_fieldsets_item(
                    obj, fieldset, "fieldsets[%d]" % index, seen_fields
                )
                for index, fieldset in enumerate(obj.fieldsets)
            )
        )


def _check_fieldsets_item(self, obj, fieldset, label, seen_fields):
    """Check an item of `fieldsets`, i.e. check that this is a pair of a
    set name and a dictionary containing "fields" key."""

    if not isinstance(fieldset, (list, tuple)):
        return must_be("a list or tuple", option=label, obj=obj, id="admin.E008")
    elif len(fieldset) != 2:
        return must_be("of length 2", option=label, obj=obj, id="admin.E009")
    elif not isinstance(fieldset[1], dict):
        return must_be(
            "a dictionary", option="%s[1]" % label, obj=obj, id="admin.E010"
        )
    elif "fields" not in fieldset[1]:
        return [
            checks.Error(
                "The value of '%s[1]' must contain the key 'fields'." % label,
                obj=obj.__class__,
                id="admin.E011",
            )
        ]
    elif not isinstance(fieldset[1]["fields"], (list, tuple)):
        return must_be(
            "a list or tuple",
            option="%s[1]['fields']" % label,
            obj=obj,
            id="admin.E008",
        )

    seen_fields.extend(flatten(fieldset[1]["fields"]))
    if len(seen_fields) != len(set(seen_fields)):
        return [
            checks.Error(
                "There are duplicate field(s) in '%s[1]'." % label,
                obj=obj.__class__,
                id="admin.E012",
            )
        ]
    return list(
        chain.from_iterable(
            self._check_field_spec(obj, fieldset_fields, '%s[1]["fields"]' % label)
            for fieldset_fields in fieldset[1]["fields"]
        )
    )
