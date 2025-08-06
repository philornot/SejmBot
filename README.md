# 🏛️ SejmBot - Parser transkryptów Sejmu RP

Automatyczny bot do pobierania i przetwarzania transkryptów z posiedzeń polskiego Sejmu.

## 📋 Opis

SejmBot to system składający się z:
- **Parsera** - automatycznie wykrywa i pobiera nowe transkrypty z sejm.gov.pl
- **Przetwarzania tekstu** - konwertuje HTML, PDF i DOCX do czystego tekstu
- **Harmonogramowania** - uruchamia się automatycznie w regularnych odstępach
- **Logowania** - śledzi wszystkie operacje i błędy

## 🚀 Szybki start

### Standardowa instalacja

```bash
# Sklonuj/pobierz pliki projektu
git clone https://github.com/your-repo/sejmbot.git
cd sejmbot

# Uruchom setup
chmod +x setup.sh
./setup.sh

# Aktywuj środowisko wirtualne
source venv/bin/activate

# Uruchom bota
python3 sejmbot.py
```

### Instalacja na Raspberry Pi

```bash
# Pobierz pliki na Pi
cd ~
git clone https://github.com/your-repo/sejmbot.git
cd sejmbot

# Uruchom instalację dla Pi (automatycznie skonfiguruje systemd)
chmod +x install_raspberry.sh
./install_raspberry.sh
```

## 📁 Struktura projektu

```
sejmbot/
├── sejmbot.py              # Główny parser
├── scheduler.py            # Harmonogram uruchamiania
├── requirements.txt        # Wymagane biblioteki
├── setup.sh               # Skrypt instalacji
├── install_raspberry.sh   # Instalacja na Pi
├── sejmbot.service        # Konfiguracja systemd
├── transkrypty/          # Pobrane transkrypty
│   ├── 2025/
│   │   ├── posiedzenie_001_abc123.json
│   │   └── posiedzenie_002_def456.json
│   └── processed_sessions.json
└── logs/                 # Pliki logów
    ├── sejmbot_20250806.log
    └── scheduler_20250806.log
```

## 🛠️ Wymagania systemowe

### Minimalne
- Python 3.7+
- 512 MB RAM
- 2 GB przestrzeni dyskowej
- Połączenie internetowe

### Rekomendowane dla Raspberry Pi
- Raspberry Pi 3B+ lub nowszy
- Karta SD 16GB Class 10
- Stałe połączenie internetowe
- Swapfile 1GB

## 📖 Używanie

### Uruchomienie jednorazowe

```bash
# Aktywuj środowisko
source venv/bin/activate

# Uruchom parser
python3 sejmbot.py
```

### Harmonogram automatyczny

```bash
# Uruchom scheduler (będzie działał w tle)
python3 scheduler.py --schedule

# Lub jednorazowo
python3 scheduler.py --once
```

### Systemd (Raspberry Pi)

```bash
# Status usługi
sudo systemctl status sejmbot

# Logi na żywo
sudo journalctl -u sejmbot -f

# Stop/start
sudo systemctl stop sejmbot
sudo systemctl start sejmbot
```

## 📊 Format danych

Każdy transkrypt zapisywany jest jako JSON:

```json
{
  "session_id": "abc123def456",
  "session_number": 15,
  "date": "2025-01-15",
  "title": "15. posiedzenie Sejmu RP",
  "url": "https://www.sejm.gov.pl/...",
  "transcript_url": "https://www.sejm.gov.pl/.../stenogram.pdf",
  "transcript_text": "Treść stenogramu...",
  "file_type": "pdf",
  "scraped_at": "2025-01-15T14:30:00",
  "hash": "md5hash_of_content"
}
```

## 🔧 Konfiguracja

Główne ustawienia w `SejmBotConfig`:

```python
user_agent = "SejmBot/1.0 (+https://github.com/sejmbot)"
delay_between_requests = 2  # sekundy
max_retries = 3
timeout = 30
```

Harmonogram w `scheduler.py`:
- Co 4 godziny w dni robocze
- Codziennie o 8:00
- W dni robocze o 14:00 (podczas sesji)

## 📝 Logi

Bot tworzy szczegółowe logi:

```
2025-01-15 14:30:15 - INFO - 🚀 Uruchomiono SejmBot
2025-01-15 14:30:16 - INFO - Przeszukuję: https://www.sejm.gov.pl/sejm10.nsf/
2025-01-15 14:30:20 - INFO - Znaleziono 5 potencjalnych sesji
2025-01-15 14:30:25 - INFO - ✅ Przetworzona sesja: 15. posiedzenie Sejmu
2025-01-15 14:30:30 - INFO - 🎉 Zakończono. Przetworzono 1 nowych sesji
```

## 🛡️ Bezpieczeństwo i etyka

- Bot respektuje `robots.txt` i limity rate
- Używa grzeczny User-Agent z kontaktem
- Nie przeciąża serwerów (delay 2s między requestami)
- Nie pobiera ponownie już przetworzonych plików
- Obsługuje błędy HTTP i timeout

## 🐛 Rozwiązywanie problemów

### Bot nie znajduje sesji
- Sprawdź czy sejm.gov.pl nie zmienił struktury
- Sprawdź logi pod kątem błędów HTTP 403/404
- Może być konieczne zaktualizowanie selektorów CSS

### Problemy z PDF/DOCX
- Upewnij się że są zainstalowane: `pdfplumber`, `docx2txt`
- Sprawdź czy pliki nie są uszkodzone
- Niektóre pliki mogą wymagać dodatkowych uprawnień

### Niska pamięć na Pi Zero
- Użyj swap file
- Zmniejsz `max_retries` i `timeout`
- Ogranicz liczbę jednoczesnych procesów

### Selenium nie działa
- Zainstaluj Chrome/Chromium: `sudo apt install chromium-browser`
- Sprawdź czy chromedriver jest w PATH
- Na Pi może być potrzebny tryb headless

## 🔄 Następne kroki (etapy 2-6)

1. **Analiza humoru** - integracja z OpenAI API
2. **Backend** - Supabase do przechowywania danych
3. **Aplikacja mobilna** - Flutter z push notifications
4. **Dashboard** - UI do monitorowania
5. **AI deployment** - optymalizacja dla edge devices

## 📄 Licencja

MIT License - użyj jak chcesz, ale na własną odpowiedzialność.

## 🤝 Wkład

Pull requesty mile widziane! Szczególnie:
- Poprawa rozpoznawania sesji
- Wsparcie dla starszych kadencji Sejmu
- Optymalizacje wydajności
- Testy jednostkowe

---

**⚠️ Uwaga**: Bot służy celom edukacyjnym i rozrywkowym. Korzystaj odpowiedzialnie i respektuj zasoby sejm.gov.pl.