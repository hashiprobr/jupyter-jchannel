class Registry:
    def __init__(self):
        self.futures = {}

    def store(self, future):
        key = id(future)
        self.futures[key] = future
        return key

    def retrieve(self, key):
        return self.futures.pop(key)

    def clear(self):
        keys = list(self.futures.keys())
        for key in keys:
            self.futures[key].cancel('Client disconnected')
            del self.futures[key]


registry = Registry()
