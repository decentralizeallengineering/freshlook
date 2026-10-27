# label: duplicate
# sample: sought
# a: django/contrib/gis/gdal/geometries.py:282 set_3d
# b: django/contrib/gis/gdal/geometries.py:296 set_measured
# why: Same boolean setter calling a capi function with 1/0 and raising ValueError; differs in capi function and message.
def set_3d(self, value):
    """Set if this geometry has Z coordinates."""
    if value is True:
        capi.set_3d(self.ptr, 1)
    elif value is False:
        capi.set_3d(self.ptr, 0)
    else:
        raise ValueError(f"Input to 'set_3d' must be a boolean, got '{value!r}'.")


def set_measured(self, value):
    """Set if this geometry has M coordinates."""
    if value is True:
        capi.set_measured(self.ptr, 1)
    elif value is False:
        capi.set_measured(self.ptr, 0)
    else:
        raise ValueError(
            f"Input to 'set_measured' must be a boolean, got '{value!r}'."
        )
