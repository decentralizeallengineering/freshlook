# label: distinct
# sample: random
# a: django/contrib/gis/db/models/functions.py:65 as_sql
# b: django/contrib/postgres/fields/array.py:358 as_sql
# why: Unrelated: spatial function name resolution vs array slice SQL.
def as_sql(self, compiler, connection, function=None, **extra_context):
    if self.function is None and function is None:
        function = connection.ops.spatial_function_name(self.name)
    return super().as_sql(compiler, connection, function=function, **extra_context)


def as_sql(self, compiler, connection):
    lhs, params = compiler.compile(self.lhs)
    # self.start is set to 1 if slice start is not provided.
    if self.end is None:
        return f"({lhs})[%s:]", (*params, self.start)
    else:
        return f"({lhs})[%s:%s]", (*params, self.start, self.end)
