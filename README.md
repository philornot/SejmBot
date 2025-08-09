# SejmBot - Parser transkryptów Sejmu RP

Bot do automatycznego pobierania i parsowania stenogramów z posiedzeń Sejmu Rzeczypospolitej Polskiej.

## Co to robi

- Automatycznie pobiera transkrypty z najnowszych posiedzeń Sejmu
- Parsuje PDFy i HTML do czytelnego tekstu  
- Zapisuje wszystko w strukturze folderów `kadencja_X/rok/`
- Nie pobiera dwukrotnie tych samych plików
- Obsługuje kadencje 6-10 (2007-2025)

## Wymagania

```bash
pip install requests beautifulsoup4 pdfplumber
```

Opcjonalnie (dla DOCX i dynamicznych stron):
```bash  
pip install docx2txt selenium
```

## Użycie

```bash
# Pojedyncze uruchomienie
python sejmbot.py

# Tryb daemon (działa w tle, sprawdza co 4h)
python sejmbot.py --daemon
```

## Struktura plików

```
transkrypty/
├── kadencja_10/
│   └── 2024/
│       ├── json/           # Transkrypty jako JSON
│       │   └── posiedzenie_039_a_XYZ123.json
│       ├── pdf/            # Oryginalne PDFy
│       │   └── posiedzenie_039_a_XYZ123.pdf  
│       └── index.json      # Indeks wszystkich sesji
├── logs/
│   └── sejmbot_20250109.log
└── processed_sessions.json  # Lista już przetworzonych
```

## Przykład danych wyjściowych

Każdy plik JSON zawiera:

```json
{
  "session_id": "10_20241218_a1b2c3d4",
  "meeting_number": 39,
  "day_letter": "a", 
  "date": "2024-12-18",
  "title": "Posiedzenie nr 39 (a) - 18 grudnia 2024 (środa)",
  "transcript_text": "Stenogram z posiedzenia...",
  "text_length": 45678,
  "word_count": 8901,
  "kadencja": 10,
  "processing_info": {
    "bot_version": "2.0",
    "processed_at": "2025-01-09T15:30:00",
    "original_pdf_available": true
  }
}
```

## Konfiguracja

Bot automatycznie:
- Konfiguruje User-Agent: `SejmBot/2.1`
- Czeka 3s między requestami (żeby nie obciążać serwera)
- Retry przy błędach połączenia (4 próby)
- Waliduje czy wyciągnięty tekst to rzeczywiście stenogram

## Problemy z którymi bot sobie radzi

- Serwer `orka2.sejm.gov.pl` często nie odpowiada → automatyczne retry
- PDFy z błędami → próbuje wyciągnąć tyle tekstu ile się da
- Zmiana struktury strony → używa wielu selektorów CSS jako fallback  
- Duplikaty → sprawdza hash treści
- Uszkodzone pliki z poprzednich wersji → automatyczne czyszczenie

## Statystyki po uruchomieniu

```
📊 PODSUMOWANIE DZIAŁANIA BOTA
═══════════════════════════════
🔍 Znalezionych dni posiedzeń:  127
⏭️  Już przetworzonych:         89
✅ Nowo przetworzonych:         23  
❌ Nieudanych:                  15
🎯 Wskaźnik sukcesu:            60.5%
```

## Techniczne detale

- **Parsowanie PDF**: `pdfplumber` (bez OCR)
- **HTML**: `BeautifulSoup` z selekcją zawartości
- **Retry logic**: Exponential backoff przy błędach
- **Walidacja**: Sprawdza czy tekst zawiera słowa kluczowe Sejmu
- **Memory safe**: Nie używa localStorage/sessionStorage  

## Dla programistów

Główne klasy:
- `SejmBotConfig` - konfiguracja URL-i, selektorów, wzorców
- `SejmBot` - główna logika scrapowania  
- `SejmSession` - dataclass reprezentująca jedno posiedzenie

Dodawanie nowej kadencji:
```python
config.kadencje[11] = {
    'base_url': 'https://www.sejm.gov.pl/Sejm11.nsf/',
    'stenogramy_url': 'https://www.sejm.gov.pl/Sejm11.nsf/stenogramy.xsp', 
    'pdf_server': 'https://orka2.sejm.gov.pl/StenoInter11.nsf/',
    'lata': list(range(2025, 2030))
}
```

## Limitacje

- Nie robi OCR (jeśli PDF to zeskanowany obraz, nie wyciągnie tekstu)
- Skupia się na stenogramach, nie pobiera innych dokumentów
- Czasem serwery Sejmu nie działają - wtedy trzeba uruchomić ponownie

## Licencja  

Transkrypty Sejmu są publiczne. Bot używa ich zgodnie z przeznaczeniem.