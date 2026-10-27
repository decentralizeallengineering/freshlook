# label: duplicate
# sample: sought
# a: django/contrib/gis/db/backends/mysql/operations.py:126 get_geometry_converter
# b: django/contrib/gis/db/backends/oracle/operations.py:230 get_geometry_converter
# why: Same WKB converter in sibling GIS backends; Oracle reads value.read() where MySQL uses value.
def get_geometry_converter(self, expression):
    read = wkb_r().read
    srid = expression.output_field.srid
    if srid == -1:
        srid = None
    geom_class = expression.output_field.geom_class

    def converter(value, expression, connection):
        if value is not None:
            geom = GEOSGeometryBase(read(memoryview(value)), geom_class)
            if srid:
                geom.srid = srid
            return geom

    return converter


def get_geometry_converter(self, expression):
    read = wkb_r().read
    srid = expression.output_field.srid
    if srid == -1:
        srid = None
    geom_class = expression.output_field.geom_class

    def converter(value, expression, connection):
        if value is not None:
            geom = GEOSGeometryBase(read(memoryview(value.read())), geom_class)
            if srid:
                geom.srid = srid
            return geom

    return converter
