from abc import ABC, abstractmethod


class AbstractFrontend(ABC):
    @abstractmethod
    def inject_file(self, url):
        """
        Injects JavaScript file.
        """

    @abstractmethod
    def inject_code(self, source):
        """
        Injects JavaScript code.
        """
