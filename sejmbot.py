#!/usr/bin/env python3
"""Pipeline: Scraper → Detektor → AI → Raport"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv  # ← Dodaj to

# Załaduj .env PRZED importami
load_dotenv()  # ← Szuka .env w CWD

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Stała: katalog danych
DATA_DIR = 'data_sejm'


def main():
    # 1. SCRAPER
    logger.info("=== KROK 1: POBIERANIE TRANSKRYPTÓW ===")
    from SejmBotScraper.core import create_scraper

    scraper = create_scraper({
        'storage': {'base_directory': DATA_DIR},
        'max_proceedings': 1,
        'fetch_full_statements': True
    })

    stats = scraper.scrape_term_statements(
        term=10,
        max_proceedings=1,
        fetch_full_statements=True
    )

    logger.info(f"Pobrano {stats.get('statements_with_full_content', 0)} wypowiedzi")

    if stats.get('statements_with_full_content', 0) == 0:
        logger.warning("Brak nowych wypowiedzi")
        return

    # 2. DETEKTOR + AI
    logger.info("=== KROK 2: WYKRYWANIE + AI ===")
    from SejmBotDetektor.main import main as detector_main

    sys.argv = [
        'detector',
        '--input-dir', DATA_DIR,
        '--output-dir', DATA_DIR,
        '--ai-evaluate',
        '--ai-min-score', '2.0',
        '--top-n', '50'
    ]

    detector_main()

    # 3. RAPORT
    logger.info("=== KROK 3: RAPORT ===")

    results_dir = Path(DATA_DIR) / 'detector_results'
    results_files = sorted(results_dir.glob('results_*.json'), key=lambda p: p.stat().st_mtime)

    if not results_files:
        logger.error("Brak wyników")
        return

    latest = results_files[-1]

    import json
    with open(latest, 'r', encoding='utf-8') as f:
        data = json.load(f)

    funny = [f for f in data.get('fragments', [])
             if f.get('ai_evaluation', {}).get('is_funny')]

    # Raport TXT
    report_path = Path('data_sejm/reports') / f'raport_{datetime.now():%Y%m%d_%H%M%S}.txt'
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"RAPORT ŚMIESZNYCH FRAGMENTÓW\n")
        f.write(f"Data: {datetime.now():%Y-%m-%d %H:%M}\n")
        f.write(f"Znaleziono: {len(funny)}/{len(data.get('fragments', []))}\n")
        f.write("=" * 80 + "\n\n")

        for i, frag in enumerate(funny[:10], 1):
            ev = frag.get('ai_evaluation', {})
            f.write(f"{i}. [{ev.get('confidence', 0):.0%}] {frag.get('text', '')[:150]}...\n")
            f.write(f"   → {ev.get('reason', '')}\n\n")

    logger.info(f"✅ Raport: {report_path}")
    logger.info(f"✅ Śmieszne: {len(funny)}")


if __name__ == '__main__':
    main()