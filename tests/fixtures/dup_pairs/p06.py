# label: distinct
# sample: random
# a: django/core/cache/backends/locmem.py:101 _delete
# b: django/core/files/storage/filesystem.py:180 delete
# why: Different operations: deleting a key from an in-memory dict vs removing a file or directory from disk.
def _delete(self, key):
    try:
        del self._cache[key]
        del self._expire_info[key]
    except KeyError:
        return False
    return True


def delete(self, name):
    if not name:
        raise ValueError("The name must be given to delete().")
    name = self.path(name)
    # If the file or directory exists, delete it from the filesystem.
    try:
        if os.path.isdir(name):
            os.rmdir(name)
        else:
            os.remove(name)
    except FileNotFoundError:
        # FileNotFoundError is raised if the file or directory was removed
        # concurrently.
        pass
