#!/bin/bash
# Instalacja SejmBot na Raspberry Pi w trybie daemon

set -e

echo "🍓 SejmBot - Instalacja daemon na Raspberry Pi"
echo "============================================="

# Sprawdź czy uruchamiamy na Pi
if [[ -f /proc/device-tree/model ]] && grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    PI_MODEL=$(tr -d '\0' < /proc/device-tree/model)
    echo "🎯 Wykryto: $PI_MODEL"
else
    echo "⚠️  Ostrzeżenie: Skrypt dedykowany dla Raspberry Pi"
    read -p "Czy chcesz kontynuować? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Sprawdź czy jesteśmy w katalogu projektu
if [[ ! -f "sejmbot.py" ]]; then
    echo "❌ Nie znaleziono sejmbot.py. Uruchom skrypt w katalogu projektu."
    exit 1
fi

CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

echo "📁 Katalog: $CURRENT_DIR"
echo "👤 Użytkownik: $CURRENT_USER"

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
    htop \
    rsync \
    logrotate

# Opcjonalnie chromium dla Selenium (jeśli potrzebne)
read -p "Czy zainstalować Chromium dla Selenium? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo apt install -y chromium-browser chromium-chromedriver
    echo "✅ Chromium zainstalowany"
fi

# Uruchom standardowy setup
echo "🚀 Uruchamianie setup.sh..."
if [[ -f "setup.sh" ]]; then
    bash setup.sh
else
    echo "⚠️  Brak setup.sh, kontynuuję..."
fi

# Dodatkowe ustawienia dla Pi
echo "🍓 Konfiguracja specyficzna dla Raspberry Pi..."

# Sprawdź pamięć RAM
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
echo "💾 Dostępna RAM: ${TOTAL_RAM}MB"

# Dodaj/zwiększ swapfile dla Pi o małej pamięci
if [[ $TOTAL_RAM -lt 2048 ]]; then
    echo "⚠️  Niska ilość RAM ($TOTAL_RAM MB), konfiguruję swap..."

    # Sprawdź obecny swap
    CURRENT_SWAP=$(free -m | awk '/^Swap:/{print $2}')

    if [[ $CURRENT_SWAP -lt 1024 ]]; then
        if [[ -f /swapfile ]]; then
            echo "📝 Zwiększanie istniejącego swapfile..."
            sudo swapoff /swapfile
        fi

        echo "💾 Tworzenie swapfile (1GB)..."
        sudo fallocate -l 1G /swapfile
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
        sudo swapon /swapfile

        # Dodaj do fstab jeśli nie ma
        if ! grep -q '/swapfile' /etc/fstab; then
            echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
        fi

        echo "✅ Swapfile skonfigurowany"
    fi
fi

# Ustaw dodatkowe zmienne środowiskowe dla Pi
echo "🔧 Konfiguracja zmiennych środowiskowych..."
if [[ ! -f venv/bin/activate ]]; then
    echo "❌ Brak wirtualnego środowiska. Uruchom najpierw setup.sh"
    exit 1
fi

# Dodaj optymalizacje do activate
cat >> venv/bin/activate << 'EOF'

# SejmBot optimizations for Raspberry Pi
export PYTHONHASHSEED=1
export PYTHONOPTIMIZE=1
export MALLOC_TRIM_THRESHOLD_=100000
export MALLOC_MMAP_THRESHOLD_=100000
EOF

# Zatrzymaj stary service jeśli istnieje
if systemctl is-active --quiet sejmbot.service 2>/dev/null; then
    echo "⏹️  Zatrzymywanie starego service..."
    sudo systemctl stop sejmbot.service
fi

if systemctl is-enabled --quiet sejmbot.service 2>/dev/null; then
    echo "❌ Wyłączanie starego service..."
    sudo systemctl disable sejmbot.service
fi

# Usuń stary plik service
if [[ -f /etc/systemd/system/sejmbot.service ]]; then
    echo "🗑️  Usuwanie starego pliku service..."
    sudo rm /etc/systemd/system/sejmbot.service
fi

# Odmaskuj service jeśli był maskowany
sudo systemctl unmask sejmbot.service 2>/dev/null || true

# Konfiguracja systemd dla Pi
echo "⚙️  Tworzenie service systemd..."

# Dostosuj limity dla modelu Pi
if [[ $PI_MODEL == *"Pi Zero"* ]]; then
    CPU_QUOTA="30%"
    MEMORY_MAX="256M"
    echo "🔧 Ustawienia dla Pi Zero: CPU 30%, RAM 256M"
elif [[ $TOTAL_RAM -lt 1024 ]]; then
    CPU_QUOTA="40%"
    MEMORY_MAX="384M"
    echo "🔧 Ustawienia dla Pi o małej RAM: CPU 40%, RAM 384M"
else
    CPU_QUOTA="60%"
    MEMORY_MAX="512M"
    echo "🔧 Ustawienia standardowe: CPU 60%, RAM 512M"
fi

sudo tee /etc/systemd/system/sejmbot.service > /dev/null << EOF
[Unit]
Description=SejmBot - Parser transkryptów Sejmu RP (Daemon Pi)
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=3

[Service]
Type=simple
Restart=on-failure
RestartSec=60
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin
Environment=PYTHONHASHSEED=1
Environment=PYTHONOPTIMIZE=1
ExecStart=$CURRENT_DIR/venv/bin/python sejmbot.py --daemon
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

# Logi z rotacją
StandardOutput=append:$CURRENT_DIR/logs/daemon.log
StandardError=append:$CURRENT_DIR/logs/daemon.log

# Ograniczenia zasobów dla Pi
CPUQuota=$CPU_QUOTA
MemoryMax=$MEMORY_MAX
OOMScoreAdjust=100

# Bezpieczeństwo
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$CURRENT_DIR

[Install]
WantedBy=multi-user.target
EOF

# Upewnij się, że katalog logs istnieje
mkdir -p logs

# Skonfiguruj rotację logów
sudo tee /etc/logrotate.d/sejmbot > /dev/null << EOF
$CURRENT_DIR/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 $CURRENT_USER $CURRENT_USER
    postrotate
        systemctl reload sejmbot.service > /dev/null 2>&1 || true
    endscript
}
EOF

# Przeładuj systemd
echo "🔄 Przeładowywanie systemd..."
sudo systemctl daemon-reload

# Włącz service
echo "⚙️  Włączanie service..."
sudo systemctl enable sejmbot.service

# Uruchom service
echo "🚀 Uruchamianie service..."
sudo systemctl start sejmbot.service

# Sprawdź status po 5 sekundach
sleep 5
echo ""
echo "📊 Status service:"
sudo systemctl status sejmbot.service --no-pager -l

# Sprawdź czy działa
sleep 3
if systemctl is-active --quiet sejmbot.service; then
    echo "✅ Service działa poprawnie!"
else
    echo "❌ Problem z uruchomieniem service"
    echo "🔍 Sprawdź logi: sudo journalctl -u sejmbot -n 20"
fi

echo ""
echo "🎉 Instalacja SejmBot daemon na Raspberry Pi zakończona!"
echo ""
echo "📋 Konfiguracja:"
echo "   • Działa 24/7 jako daemon"
echo "   • Pobiera transkrypty co 4 godziny"
echo "   • Automatyczny restart po awarii"
echo "   • Optymalizacje dla Pi ($PI_MODEL)"
echo "   • Rotacja logów (7 dni)"
echo "   • CPU limit: $CPU_QUOTA, RAM limit: $MEMORY_MAX"
echo ""
echo "🔧 Przydatne komendy:"
echo "   sudo systemctl status sejmbot      # Status"
echo "   sudo systemctl restart sejmbot     # Restart"
echo "   sudo journalctl -u sejmbot -f      # Logi systemd"
echo "   tail -f logs/daemon.log            # Logi aplikacji"
echo "   htop                               # Monitor zasobów"
echo ""
echo "📁 Pliki:"
echo "   Logi: $CURRENT_DIR/logs/"
echo "   Transkrypty: $CURRENT_DIR/transkrypty/"
echo "   Service: /etc/systemd/system/sejmbot.service"
echo ""
echo "🍓 SejmBot gotowy do pracy na Pi!"