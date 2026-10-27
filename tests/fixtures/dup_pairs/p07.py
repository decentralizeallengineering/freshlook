# label: distinct
# sample: random
# a: django/contrib/gis/db/models/sql/conversion.py:52 get_prep_value
# b: django/contrib/postgres/fields/ranges.py:89 get_prep_value
# why: Different conversions: Distance passthrough vs Range/list/tuple coercion to a range type.
def get_prep_value(self, value):
    if isinstance(value, Distance):
        return value
    return super().get_prep_value(value)


def get_prep_value(self, value):
    if value is None:
        return None
    elif isinstance(value, Range):
        return value
    elif isinstance(value, (list, tuple)):
        return self.range_type(value[0], value[1])
    return value
