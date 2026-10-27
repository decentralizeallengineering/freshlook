# label: distinct
# sample: random
# a: django/core/files/storage/base.py:20 open
# b: django/core/files/storage/memory.py:54 open
# why: Different: storage open delegates to _open; in-memory file open converts stream and updates access time before super().
def open(self, name, mode="rb"):
    """Retrieve the specified file from storage."""
    return self._open(name, mode)


def open(self, mode):
    self._convert_stream_content(mode)
    self._update_accessed_time()
    return super().open(mode)
