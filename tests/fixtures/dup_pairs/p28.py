# label: duplicate
# sample: sought
# a: django/contrib/sessions/backends/cache.py:125 delete
# b: django/contrib/sessions/backends/cached_db.py:106 delete
# why: Same cache session delete; the cached_db copy adds one leading super().delete() call.
def delete(self, session_key=None):
    if session_key is None:
        if self.session_key is None:
            return
        session_key = self.session_key
    self._cache.delete(self.cache_key_prefix + session_key)


def delete(self, session_key=None):
    super().delete(session_key)
    if session_key is None:
        if self.session_key is None:
            return
        session_key = self.session_key
    self._cache.delete(self.cache_key_prefix + session_key)
