# label: distinct
# sample: random
# a: django/contrib/gis/geos/geometry.py:293 crosses
# b: django/contrib/gis/geos/geometry.py:308 equals
# why: One-line wrappers around different GEOS predicates; trivial boilerplate.
def crosses(self, other):
    """
    Return true if the DE-9IM intersection matrix for the two Geometries
    is T*T****** (for a point and a curve,a point and an area or a line and
    an area) 0******** (for two curves).
    """
    return capi.geos_crosses(self.ptr, other.ptr)


def equals(self, other):
    """
    Return true if the DE-9IM intersection matrix for the two Geometries
    is T*F**FFF*.
    """
    return capi.geos_equals(self.ptr, other.ptr)
