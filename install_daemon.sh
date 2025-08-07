#!/bin/bash
# Instalacja SejmBot w trybie daemon

set -e

echo "🔄 SejmBot - Instalacja trybu daemon"
echo "=================================="

# Sprawdź czy jesteśmy w katalogu projektu
if [[ ! -f "sejmbot.py" ]]; then
    echo "❌ Nie znaleziono sejmbot.py. Uruchom skrypt w katalogu projektu."
    exit 1
fi

CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

echo "📁 Katalog: $CURRENT_DIR"
echo "👤 Użytkownik: $CURRENT_USER"

# Zatrzymaj i wyłącz stary service jeśli istnieje
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

# Utwórz nowy plik service
echo "📝 Tworzenie nowego pliku service..."
sudo tee /etc/systemd/system/sejmbot.service > /dev/null << EOF
[Unit]
Description=SejmBot - Parser transkryptów Sejmu RP (Daemon)
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
# Uruchamiaj główny bot jako daemon (nie scheduler!)
ExecStart=$CURRENT_DIR/venv/bin/python sejmbot.py --daemon
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

# Logi
StandardOutput=append:$CURRENT_DIR/logs/daemon.log
StandardError=append:$CURRENT_DIR/logs/daemon.log

# Ograniczenia zasobów dla Pi
CPUQuota=50%
MemoryMax=512M
OOMScoreAdjust=100

# Bezpieczeństwo
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Upewnij się, że katalog logs istnieje
mkdir -p logs

# Przeładuj systemd
echo "🔄 Przeładowywanie systemd..."
sudo systemctl daemon-reload

# Włącz service (będzie uruchamiany przy starcie systemu)
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

echo ""
echo "✅ Instalacja daemon mode zakończona!"
echo ""
echo "📋 Service będzie:"
echo "   • Uruchamiany automatycznie po starcie systemu"
echo "   • Działał ciągle w tle"
echo "   • Pobierał transkrypty co 4 godziny"
echo "   • Restartował się automatycznie po błędzie"
echo ""
echo "🔧 Przydatne komendy:"
echo "   sudo systemctl status sejmbot     # Status"
echo "   sudo systemctl stop sejmbot       # Stop"
echo "   sudo systemctl start sejmbot      # Start"
echo "   sudo systemctl restart sejmbot    # Restart"
echo "   sudo journalctl -u sejmbot -f     # Logi systemd (live)"
echo "   tail -f logs/daemon.log           # Logi aplikacji (live)"
echo ""
echo "📁 Pliki:"
echo "   Logi daemon: $CURRENT_DIR/logs/daemon.log"
echo "   Transkrypty: $CURRENT_DIR/transkrypty/"
echo ""
echo "🎉 SejmBot daemon gotowy do pracy 24/7!"