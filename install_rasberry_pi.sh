#!/bin/bash
# Instalacja SejmBot na Raspberry Pi

set -e

echo "🍓 SejmBot - Instalacja na Raspberry Pi"
echo "======================================"

# Sprawdź czy uruchamiamy na Pi
if [[ ! -f /proc/device-tree/model ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "⚠️  Ostrzeżenie: Skrypt dedykowany dla Raspberry Pi"
    read -p "Czy chcesz kontynuować? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Aktualizuj system
echo "📦 Aktualizacja systemu..."
sudo apt update && sudo apt upgrade -y

# Zainstaluj wymagane pakiety systemowe
echo "🔧 Instalacja pakietów systemowych..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    chromium-browser \
    chromium-chromedriver

# Sprawdź czy jesteśmy w katalogu projektu
if [[ ! -f "sejmbot.py" ]]; then
    echo "❌ Nie znaleziono sejmbot.py. Uruchom skrypt w katalogu projektu."
    exit 1
fi

# Uruchom standardowy setup
echo "🚀 Uruchamianie setup.sh..."
bash setup.sh

# Dodatkowe ustawienia dla Pi
echo "🍓 Konfiguracja specyficzna dla Raspberry Pi..."

# Dodaj swapfile jeśli nie ma
if [[ ! -f /swapfile ]]; then
    echo "💾 Tworzenie swapfile (1GB)..."
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

# Ustaw limity pamięci dla Pi Zero
PI_MODEL=$(tr -d '\0' < /proc/device-tree/model)
if [[ $PI_MODEL == *"Pi Zero"* ]]; then
    echo "🔧 Dostosowania dla Pi Zero..."
    # Dodatkowe ustawienia dla niskiej pamięci
    echo "export PYTHONHASHSEED=1" >> venv/bin/activate
    echo "export PYTHONOPTIMIZE=1" >> venv/bin/activate
fi

# Konfiguracja systemd
echo "⚙️  Instalacja usługi systemd..."
sudo cp sejmbot.service /etc/systemd/system/
sudo systemctl daemon-reload

# Dostosuj ścieżki w pliku service
CURRENT_DIR=$(pwd)
sudo sed -i "s|/home/pi/sejmbot|$CURRENT_DIR|g" /etc/systemd/system/sejmbot.service

# Sprawdź czy user pi istnieje, jeśli nie - użyj bieżącego
CURRENT_USER=$(whoami)
if [[ $CURRENT_USER != "pi" ]]; then
    sudo sed -i "s/User=pi/User=$CURRENT_USER/g" /etc/systemd/system/sejmbot.service
    sudo sed -i "s/Group=pi/Group=$CURRENT_USER/g" /etc/systemd/system/sejmbot.service
fi

# Włącz i uruchom usługę
echo "🎬 Uruchamianie usługi..."
sudo systemctl enable sejmbot.service
sudo systemctl start sejmbot.service

# Sprawdź status
sleep 3
echo ""
echo "📊 Status usługi:"
sudo systemctl status sejmbot.service --no-pager

echo ""
echo "✅ Instalacja zakończona!"
echo ""
echo "Przydatne komendy:"
echo "  sudo systemctl status sejmbot    # Status"
echo "  sudo systemctl logs sejmbot      # Logi"
echo "  sudo systemctl stop sejmbot      # Stop"
echo "  sudo systemctl start sejmbot     # Start"
echo "  sudo systemctl restart sejmbot   # Restart"
echo ""
echo "Logi aplikacji: $CURRENT_DIR/logs/"
echo "Transkrypty: $CURRENT_DIR/transkrypty/"
echo ""
echo "🎉 SejmBot gotowy do pracy!"