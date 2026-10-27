# label: distinct
# sample: random
# a: django/contrib/gis/db/models/functions.py:445 as_sql
# b: django/contrib/postgres/fields/ranges.py:36 as_sql
# why: Unrelated: geodetic support check before delegating vs returning a literal range bounds string.
def as_sql(self, compiler, connection, **extra_context):
    if (
        self.geo_field.geodetic(connection)
        and not connection.features.supports_length_geodetic
    ):
        raise NotSupportedError(
            "This backend doesn't support Length on geodetic fields"
        )
    return super().as_sql(compiler, connection, **extra_context)


def as_sql(self, compiler, connection):
    return "'%s%s'" % (self.lower, self.upper), []
