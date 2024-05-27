class Registry:
    def __init__(self):
        self._futures = {}

    def store(self, future):
        key = id(future)
        self._futures[key] = future
        return key

    def retrieve(self, key):
        return self._futures.pop(key)

    def clear(self):
        keys = list(self._futures.keys())
        for key in keys:
            future = self._futures.pop(key)
            future.cancel('Server disconnected')
