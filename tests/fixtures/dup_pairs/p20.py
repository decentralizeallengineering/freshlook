# label: duplicate
# sample: sought
# a: django/core/handlers/asgi.py:114 _get_post
# b: django/core/handlers/wsgi.py:91 _get_post
# why: Exact copy of lazy POST loading in the ASGI and WSGI request classes.
def _get_post(self):
    if not hasattr(self, "_post"):
        self._load_post_and_files()
    return self._post


def _get_post(self):
    if not hasattr(self, "_post"):
        self._load_post_and_files()
    return self._post
