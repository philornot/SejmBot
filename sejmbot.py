#!/usr/bin/env python3
"""
Pełny pipeline: Scraper → Detektor → AI → Raport
Uruchom: python sejmbot.py
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Główny pipeline"""

    # 1. SCRAPER - pobierz najnowsze transkrypty
    logger.info("=== KROK 1: POBIERANIE TRANSKRYPTÓW ===")
    from SejmBotScraper.core import create_scraper

    scraper = create_scraper({
        'max_proceedings': 1,  # Tylko najnowsze posiedzenie
        'fetch_full_statements': True
    })

    stats = scraper.scrape_term_statements(
        term=10,
        max_proceedings=1,
        fetch_full_statements=True
    )

    logger.info(f"Pobrano {stats.get('statements_with_full_content', 0)} wypowiedzi z treścią")

    if stats.get('statements_with_full_content', 0) == 0:
        logger.warning("Brak nowych wypowiedzi - koniec")
        return

    # 2. DETEKTOR - znajdź śmieszne fragmenty
    logger.info("=== KROK 2: WYKRYWANIE FRAGMENTÓW ===")
    from SejmBotDetektor.main import main as detector_main

    # Uruchom detektor z AI
    sys.argv = [
        'detector',
        '--ai-evaluate',
        '--ai-min-score', '2.0',
        '--top-n', '50'
    ]

    detector_main()

    # 3. RAPORT - znajdź najnowszy plik z wynikami
    logger.info("=== KROK 3: GENEROWANIE RAPORTU ===")

    detector_results = Path('data/detector_results')
    if not detector_results.exists():
        logger.error("Brak wyników detektora")
        return

    # Znajdź najnowszy plik
    results_files = sorted(detector_results.glob('results_*.json'), key=lambda p: p.stat().st_mtime)
    if not results_files:
        logger.error("Brak plików z wynikami")
        return

    latest = results_files[-1]
    logger.info(f"Najnowszy plik wyników: {latest}")

    # Wczytaj i filtruj śmieszne
    import json
    with open(latest, 'r', encoding='utf-8') as f:
        data = json.load(f)

    funny_fragments = [
        f for f in data.get('fragments', [])
        if f.get('ai_evaluation', {}).get('is_funny', False)
    ]

    # Generuj prosty raport
    report_path = Path('data/reports') / f'raport_{datetime.now():%Y%m%d_%H%M%S}.txt'
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"RAPORT ŚMIESZNYCH FRAGMENTÓW\n")
        f.write(f"Data: {datetime.now():%Y-%m-%d %H:%M}\n")
        f.write(f"Znaleziono: {len(funny_fragments)} fragmentów\n")
        f.write("=" * 80 + "\n\n")

        for i, frag in enumerate(funny_fragments[:10], 1):  # Top 10
            eval_data = frag.get('ai_evaluation', {})
            f.write(f"{i}. FRAGMENT (pewność: {eval_data.get('confidence', 0):.0%})\n")
            f.write(f"   {frag.get('text', '')[:200]}...\n")
            f.write(f"   Powód: {eval_data.get('reason', 'brak')}\n\n")

    logger.info(f"✅ Raport zapisany: {report_path}")
    logger.info(f"✅ Znaleziono {len(funny_fragments)} śmiesznych fragmentów")


if __name__ == '__main__':
    main()