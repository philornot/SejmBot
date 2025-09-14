"""Moduł storage"""
try:
    from .file_manager import FileManagerInterface

    __all__ = ['FileManagerInterface']
except ImportError:
    __all__ = []
