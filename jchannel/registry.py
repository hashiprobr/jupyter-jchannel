# Copyright (c) 2024 Marcelo Hashimoto
#
# This program and the accompanying materials are made
# available under the terms of the Eclipse Public License 2.0
# which is available at https://www.eclipse.org/legal/epl-2.0/
#
# SPDX-License-Identifier: EPL-2.0


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
