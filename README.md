# SejmBot - Parser transkryptów Sejmu RP

🤖 Automatyczny bot do pobierania i parsowania stenogramów z posiedzeń Sejmu Rzeczypospolitej Polskiej.

## 🎯 Co robi

- Pobiera transkrypty z najnowszych posiedzeń Sejmu
- Parsuje PDFy i HTML do czystego tekstu
- Zapisuje w strukturze `kadencja_X/rok/`
- Nie pobiera duplikatów
- Działa 24/7 w tle (co 4 godziny)
- Optymalizowany dla Raspberry Pi Zero 2W

## ⚡ Szybki start

```bash
# Pobierz kod
git clone https://github.com/philornot/SejmBot
cd sejmbot

# Uruchom setup (robi wszystko automatycznie)
./setup.sh

# Test ręczny
./venv/bin/python main.py
```

**Gotowe!** Bot działa automatycznie co 4 godziny.

## 📋 Wymagania

- **Python 3.7+**
- **50MB wolnego miejsca** (na kod i cache)
- **Dostęp do internetu**

### Testowane systemy

- ✅ Raspberry Pi Zero 2W (Raspberry Pi OS)
- ✅ Ubuntu 20.04+
- ✅ Debian 11+
- ✅ macOS 12+

## 📂 Struktura plików

```
sejmbot/
├── main.py           # Główny bot (twój kod)
├── transkrypty/         # Pobrane stenogramy
│   └── kadencja_10/
│       └── 2024/
│           ├── json/    # JSON z tekstem
│           └── pdf/     # Oryginalne PDFy
├── logs/               # Logi działania
│   ├── sejmbot_2025*.log
│   └── cron.log
└── venv/               # Środowisko Python
```

## 🔧 Zarządzanie

```bash
# Status harmonogramu
crontab -l

# Logi na żywo  
tail -f logs/sejmbot_$(date +%Y%m%d).log

# Ręczne uruchomienie
./venv/bin/python main.py

# Zatrzymanie automatyki
crontab -r
```

## 📊 Przykład danych wyjściowych

```json
{
  "session_id": "10_20241218_a1b2c3d4",
  "meeting_number": 39,
  "date": "2024-12-18",
  "title": "Posiedzenie nr 39 (a) - 18 grudnia 2024",
  "transcript_text": "Stenogram z posiedzenia...",
  "word_count": 8901,
  "kadencja": 10,
  "processed_at": "2025-01-09T15:30:00"
}
```

## 🍓 Raspberry Pi Zero 2W

Bot jest **zoptymalizowany dla Pi Zero**:

- Zużywa ~30MB RAM
- Minimalne obciążenie CPU
- Automatyczne optymalizacje systemowe
- Bezpieczne dla karty SD

```bash
# Monitoring na Pi
free -h                    # RAM
df -h                      # Miejsce na dysku  
vcgencmd measure_temp      # Temperatura
```

## 🔍 Jak to działa

1. **Skanowanie:** Bot odwiedza stronę Sejmu co 4h
2. **Wykrywanie:** Szuka nowych posiedzeń
3. **Pobieranie:** Ściąga PDFy/HTML
4. **Parsowanie:** Wyciąga czysty tekst
5. **Zapis:** Strukturyzuje jako JSON + archiwum PDF
6. **Logowanie:** Zapisuje co się działo

## 📚 Użyte biblioteki

| Biblioteka        | Przeznaczenie           |
|-------------------|-------------------------|
| `requests`        | Pobieranie stron/plików |
| `beautifulsoup4`  | Parsowanie HTML         |
| `lxml`            | Szybkie parsowanie XML  |
| `pypdf`           | Odczyt PDF (lekki)      |
| `python-dateutil` | Obsługa dat             |

## 🚨 Rozwiązywanie problemów

### Bot nie pobiera nowych transkryptów

```bash
# Sprawdź logi
tail -20 logs/sejmbot_$(date +%Y%m%d).log

# Test ręczny
./venv/bin/python main.py
```

### Brak miejsca na Pi

```bash
# Wyczyść stare logi (starsze niż 7 dni)
find logs/ -name "*.log" -mtime +7 -delete

# Wyczyść stare PDFy (opcjonalnie)
find transkrypty/ -name "*.pdf" -mtime +30 -delete
```

### Serwer Sejmu nie odpowiada

**To normalne.** Bot automatycznie powtarza próby (4x z odstępami).

## 🎯 Statystyki

Po uruchomieniu bot pokazuje:

```
📊 PODSUMOWANIE
═══════════════
🔍 Znalezione posiedzenia: 127
✅ Nowo pobrane:           23  
❌ Błędy:                  15
🎯 Wskaźnik sukcesu:       60.5%
```

## 📄 Licencja

Stenogramy Sejmu są **publicznie dostępne**. Bot używa ich zgodnie z przeznaczeniem.

Kod bota jest na licencji MIT.