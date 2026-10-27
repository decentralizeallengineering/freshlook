# label: duplicate
# sample: random
# a: django/contrib/gis/db/backends/postgis/operations.py:411 get_geometry_converter
# b: django/contrib/gis/db/backends/spatialite/operations.py:224 get_geometry_converter
# why: Same WKB geometry converter; the PostGIS copy adds one statement encoding hex str values to bytes.
def get_geometry_converter(self, expression):
    read = wkb_r().read
    geom_class = expression.output_field.geom_class

    def converter(value, expression, connection):
        if isinstance(value, str):  # Coming from hex strings.
            value = value.encode("ascii")
        return None if value is None else GEOSGeometryBase(read(value), geom_class)

    return converter


def get_geometry_converter(self, expression):
    geom_class = expression.output_field.geom_class
    read = wkb_r().read

    def converter(value, expression, connection):
        return None if value is None else GEOSGeometryBase(read(value), geom_class)

    return converter
