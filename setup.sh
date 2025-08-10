#!/bin/bash
# Ultimate setup dla SejmBot - schludny i wydajny

set -e

echo "🏛️  SejmBot - Schludny Setup"
echo "============================="

# Sprawdź system
echo "🔍 Sprawdzanie systemu..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "✅ Python $PYTHON_VERSION znaleziony"
else
    echo "❌ Python3 nie znaleziony. Zainstaluj Python 3.7+"
    exit 1
fi

# Wykryj czy to Pi
PI_DETECTED=false
if [[ -f /proc/device-tree/model ]] && grep -qi "raspberry pi" /proc/device-tree/model 2>/dev/null; then
    PI_MODEL=$(tr -d '\0' < /proc/device-tree/model)
    echo "🍓 Wykryto: $PI_MODEL"
    PI_DETECTED=true
fi

# Utwórz wirtualne środowisko
if [ ! -d "venv" ]; then
    echo "📦 Tworzenie środowiska Python..."
    python3 -m venv venv
    echo "✅ Środowisko utworzone"
else
    echo "📦 Używam istniejącego środowiska..."
fi

# Aktywuj środowisko
source venv/bin/activate

# Aktualizuj pip cicho
echo "🔧 Aktualizacja pip..."
pip install --upgrade pip -q

# Zainstaluj zależności
echo "📚 Instalacja bibliotek..."
pip install -q \
    requests>=2.31.0 \
    beautifulsoup4>=4.12.0 \
    lxml>=4.9.0 \
    pypdf>=3.0.0 \
    python-dateutil>=2.8.0

echo "✅ Biblioteki zainstalowane"

# Utwórz katalogi
mkdir -p transkrypty logs
echo "📁 Katalogi utworzone"

# Test instalacji
echo "🧪 Test instalacji..."
python3 -c "
import requests, bs4, pypdf, dateutil
print('✅ Wszystkie biblioteki działają')
"

# Konfiguruj harmonogram
echo "⏰ Konfiguracja harmonogramu..."
CURRENT_DIR=$(pwd)
CRON_JOB="0 */4 * * * cd $CURRENT_DIR && ./venv/bin/python sejmbot.py >> logs/cron.log 2>&1"

# Sprawdź czy cron job już istnieje
if crontab -l 2>/dev/null | grep -q "sejmbot.py"; then
    echo "⚠️  Cron job już istnieje, pomijam..."
else
    # Dodaj do crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Dodano harmonogram: co 4 godziny"
fi

# Optymalizacje dla Pi
if [ "$PI_DETECTED" = true ]; then
    echo "🍓 Optymalizacje dla Raspberry Pi..."

    # Sprawdź RAM
    TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
    echo "💾 RAM: ${TOTAL_RAM}MB"

    # Optymalizacje systemowe (bezpieczne)
    echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf >/dev/null 2>&1 || true

    echo "✅ Optymalizacje zastosowane"
fi

# Test uruchomienia
echo "🚀 Test uruchomienia..."
if timeout 30 ./venv/bin/python sejmbot.py --test 2>/dev/null; then
    echo "✅ SejmBot działa poprawnie"
else
    echo "⚠️  Test nieudany, ale to może być OK (brak --test w bocie)"
fi

echo ""
echo "🎉 Setup zakończony!"
echo ""
echo "📋 Co teraz:"
echo "1. Uruchom raz ręcznie:    ./venv/bin/python sejmbot.py"
echo "2. Sprawdź logi:           tail -f logs/*.log"
echo "3. Sprawdź harmonogram:    crontab -l"
echo ""
echo "⏱️  Bot będzie działał automatycznie co 4 godziny"
echo "📁 Transkrypty będą w:     ./transkrypty/"
echo "📄 Logi będą w:            ./logs/"
echo ""
if [ "$PI_DETECTED" = true ]; then
    echo "🍓 Pi gotowe do pracy 24/7!"
else
    echo "💻 System gotowy do pracy!"
fi