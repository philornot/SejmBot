#!/bin/bash
# Setup script dla SejmBot

set -e

echo "🏛️  SejmBot - Setup"
echo "=================="

# Sprawdź czy Python3 jest dostępny
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 nie został znaleziony. Zainstaluj Python 3.7+"
    exit 1
fi

# Sprawdź wersję Python
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Python version: $python_version"

# Utwórz wirtualne środowisko
if [ ! -d "venv" ]; then
    echo "📦 Tworzenie wirtualnego środowiska..."
    python3 -m venv venv
fi

# Aktywuj środowisko
echo "🔧 Aktywowanie środowiska..."
source venv/bin/activate

# Aktualizuj pip
echo "⬆️  Aktualizacja pip..."
pip install --upgrade pip

# Zainstaluj wymagania
echo "📚 Instalacja bibliotek..."
pip install -r requirements.txt

# Utwórz katalogi
echo "📁 Tworzenie katalogów..."
mkdir -p transkrypty logs

# Sprawdź instalację
echo "🧪 Testowanie instalacji..."
python3 -c "
import requests, bs4, json, pathlib, logging, signal, time, threading
try:
    import pdfplumber
    print('✅ PDF support: OK')
except ImportError:
    print('⚠️  PDF support: Brak (zainstaluj pdfplumber)')

try:
    import docx2txt
    print('✅ DOCX support: OK')
except ImportError:
    print('⚠️  DOCX support: Brak (zainstaluj docx2txt)')

try:
    import selenium
    print('✅ Selenium support: OK')
except ImportError:
    print('⚠️  Selenium support: Brak (opcjonalne)')

print('🚀 Instalacja zakończona pomyślnie!')
"

echo ""
echo "✅ Setup zakończony!"
echo ""
echo "🎯 Sposoby uruchamiania SejmBot:"
echo ""
echo "1️⃣  Jednorazowe uruchomienie:"
echo "   source venv/bin/activate"
echo "   python3 sejmbot.py"
echo ""
echo "2️⃣  Tryb daemon (zalecany dla serwera):"
echo "   source venv/bin/activate"
echo "   python3 sejmbot.py --daemon"
echo ""
echo "3️⃣  W tle (ręcznie):"
echo "   nohup python3 sejmbot.py --daemon > logs/daemon.log 2>&1 &"
echo ""
echo "4️⃣  Jako systemd service (najlepsze dla produkcji):"
echo "   ./install_daemon.sh  # dla trybu 24/7"
echo ""
echo "💡 Dla Raspberry Pi użyj: ./install_rasberry_pi_daemon.sh"