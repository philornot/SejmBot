"""Moduł scraping"""
try:
    from .scraper import SejmScraper

    __all__ = ['SejmScraper']
except ImportError:
    __all__ = []
