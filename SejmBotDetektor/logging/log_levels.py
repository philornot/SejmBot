"""
Poziomy logowania dla SejmBot Detektora
"""
from enum import Enum


class LogLevel(Enum):
    """Poziomy logowania"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"LogLevel.{self.name}"

    @classmethod
    def from_string(cls, level_str: str):
        """Tworzy LogLevel z nazwy tekstowej"""
        level_str = level_str.upper()
        for level in cls:
            if level.value == level_str:
                return level
        raise ValueError(f"Nieznany poziom logowania: {level_str}")

    @classmethod
    def get_all_levels(cls):
        """Zwraca wszystkie dostępne poziomy"""
        return list(cls)

    def get_priority(self) -> int:
        """Zwraca priorytet poziom (wyższy = ważniejszy)"""
        priorities = {
            "DEBUG": 0,
            "INFO": 1,
            "SUCCESS": 2,
            "WARNING": 3,
            "ERROR": 4,
            "CRITICAL": 5
        }
        return priorities[self.value]

    def __ge__(self, other):
        """Pozwala na porównywanie poziomów"""
        if not isinstance(other, LogLevel):
            return NotImplemented
        return self.get_priority() >= other.get_priority()

    def __gt__(self, other):
        """Pozwala na porównywanie poziomów"""
        if not isinstance(other, LogLevel):
            return NotImplemented
        return self.get_priority() > other.get_priority()

    def __le__(self, other):
        """Pozwala na porównywanie poziomów"""
        if not isinstance(other, LogLevel):
            return NotImplemented
        return self.get_priority() <= other.get_priority()

    def __lt__(self, other):
        """Pozwala na porównywanie poziomów"""
        if not isinstance(other, LogLevel):
            return NotImplemented
        return self.get_priority() < other.get_priority()

    def __eq__(self, other):
        """Pozwala na porównywanie poziomów"""
        if not isinstance(other, LogLevel):
            return NotImplemented
        return self.get_priority() == other.get_priority()
