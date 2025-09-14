"""Moduł CLI"""
try:
    from .commands import CLICommands

    __all__ = ['CLICommands']
except ImportError:
    __all__ = []
