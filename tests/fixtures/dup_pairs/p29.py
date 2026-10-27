# label: duplicate
# sample: sought
# a: django/contrib/gis/db/backends/postgis/operations.py:213 convert_extent
# b: django/contrib/gis/db/backends/postgis/operations.py:226 convert_extent3d
# why: Same BOX text parser; the 3D copy uses a different prefix offset and an extra z coordinate.
def convert_extent(self, box):
    """
    Return a 4-tuple extent for the `Extent` aggregate by converting
    the bounding box text returned by PostGIS (`box` argument), for
    example: "BOX(-90.0 30.0, -85.0 40.0)".
    """
    if box is None:
        return None
    ll, ur = box[4:-1].split(",")
    xmin, ymin = map(float, ll.split())
    xmax, ymax = map(float, ur.split())
    return (xmin, ymin, xmax, ymax)


def convert_extent3d(self, box3d):
    """
    Return a 6-tuple extent for the `Extent3D` aggregate by converting
    the 3d bounding-box text returned by PostGIS (`box3d` argument), for
    example: "BOX3D(-90.0 30.0 1, -85.0 40.0 2)".
    """
    if box3d is None:
        return None
    ll, ur = box3d[6:-1].split(",")
    xmin, ymin, zmin = map(float, ll.split())
    xmax, ymax, zmax = map(float, ur.split())
    return (xmin, ymin, zmin, xmax, ymax, zmax)
