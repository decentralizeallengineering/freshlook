# label: duplicate
# sample: sought
# a: django/core/cache/backends/memcached.py:92 get_many
# b: django/core/cache/backends/redis.py:201 get_many
# why: Same get_many key-mapping logic in sibling cache backends; only the client method name differs (get_multi vs get_many).
def get_many(self, keys, version=None):
    key_map = {
        self.make_and_validate_key(key, version=version): key for key in keys
    }
    ret = self._cache.get_multi(key_map.keys())
    return {key_map[k]: v for k, v in ret.items()}


def get_many(self, keys, version=None):
    key_map = {
        self.make_and_validate_key(key, version=version): key for key in keys
    }
    ret = self._cache.get_many(key_map.keys())
    return {key_map[k]: v for k, v in ret.items()}
