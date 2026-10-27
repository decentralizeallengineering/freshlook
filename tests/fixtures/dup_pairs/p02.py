# label: distinct
# sample: random
# a: django/contrib/gis/gdal/srs.py:214 linear_name
# b: django/contrib/gis/gdal/srs.py:220 linear_units
# why: Both are 2-line accessors around the same capi call returning different tuple elements; trivial, not worth merging.
@property
def linear_name(self):
    "Return the name of the linear units."
    units, name = capi.linear_units(self.ptr, byref(c_char_p()))
    return name


@property
def linear_units(self):
    "Return the value of the linear units."
    units, name = capi.linear_units(self.ptr, byref(c_char_p()))
    return units
