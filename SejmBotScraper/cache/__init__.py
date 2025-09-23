"""Moduł cache"""
try:
    from .manager import CacheInterface

    __all__ = ['CacheInterface']
except ImportError:
    __all__ = []
