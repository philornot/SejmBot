"""Moduł API"""
try:
    from .client import SejmAPIInterface

    __all__ = ['SejmAPIInterface']
except ImportError:
    __all__ = []
