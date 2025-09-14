"""Moduł scheduler"""
try:
    from .scheduler import SejmScheduler

    __all__ = ['SejmScheduler']
except ImportError:
    __all__ = []
