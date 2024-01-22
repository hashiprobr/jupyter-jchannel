class Registry:
    def __init__(self):
        self.futures = {}

    def store(self, future):
        key = id(future)
        self.futures[key] = future
        return key

    def retrieve(self, key):
        return self.futures.pop(key)


registry = Registry()
