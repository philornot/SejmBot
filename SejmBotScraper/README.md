# SejmBot-scraper

Narzędzie do automatycznego pobierania stenogramów z posiedzeń Sejmu Rzeczypospolitej Polskiej za pomocą
oficjalnego API. Stworzony jako część projektu **SejmBot** — systemu wykrywającego śmieszne momenty z polskiego
parlamentu.

## Opis

SejmBot-scraper wykorzystuje oficjalne API Sejmu RP do pobierania:

- Stenogramów w formacie PDF z całych dni posiedzeń
- Poszczególnych wypowiedzi w formacie HTML
- Metadanych dotyczących posiedzeń i wypowiedzi

Program automatycznie organizuje pobrane pliki w przejrzystą strukturę folderów i jest przygotowany do integracji z
systemami automatyzacji.

## Struktura projektu

```
SejmBot-scraper/
├── main.py              # Główny plik uruchamiający
├── sejm_api.py          # Komunikacja z API Sejmu
├── scraper.py           # Główna logika scrapowania
├── file_manager.py      # Zarządzanie plikami i folderami
├── config.py            # Konfiguracja programu
├── API.md               # Dokumentacja API Sejmu RP
├── requirements.txt     # Zależności Python
└── README.md           # Ta dokumentacja
```

## Funkcje

- **Inteligentne filtrowanie**: Automatycznie pomija duplikaty i przyszłe posiedzenia
- **Szczegółowe statystyki**: Raportuje postęp, błędy, pominięte posiedzenia
- **Metadane**: Zapisuje strukturalne informacje o posiedzeniach w JSON
- **Obsługa błędów**: Rozróżnia błędy rzeczywiste od normalnych braków danych
- **Production-ready**: Robust error handling, rate limiting, szczegółowe logowanie
- **CLI z wieloma opcjami**: Elastyczne konfigurowanie pobierania

## Użycie

### Podstawowe użycie

```bash
# Pobierz całą 10. kadencję (tylko PDF-y)
python main.py

# Pobierz konkretną kadencję
python main.py -t 9

# Pobierz konkretne posiedzenie
python main.py -t 10 -p 15
```

### Opcje pobierania

```bash
# Pobierz także wypowiedzi HTML
python main.py -t 10 --statements

# Nie pobieraj PDF-ów
python main.py -t 10 --no-pdfs --statements

# Szczegółowe logi
python main.py -v

# Zapisz logi do pliku
python main.py --log-file scraper.log
```

### Opcje informacyjne

```bash
# Wyświetl dostępne kadencje
python main.py --list-terms

# Wyświetl podsumowanie posiedzeń danej kadencji
python main.py -t 10 --summary
```

## Struktura wyjściowa

Program tworzy następującą strukturę folderów:

```
stenogramy_sejm/
└── kadencja_10/
    ├── posiedzenie_001_2023-11-13/
    │   ├── info_posiedzenia.json      # Metadane posiedzenia
    │   ├── transkrypt_2023-11-13.pdf
    │   ├── transkrypt_2023-11-14.pdf
    │   └── wypowiedzi_2023-11-13/
    │       ├── 001_Marszalek_Sejmu.html
    │       ├── 002_Jan_Kowalski.html
    │       └── ...
    └── posiedzenie_002_2023-11-20/
        └── ...
```

## Automatyzacja

SejmBot-scraper jest przygotowany do integracji z systemami automatyzacji:

- **Kompatybilny z cron jobs**: Szczegółowe logi, return codes
- **Built-in scheduler**: (w rozwoju)
- **Monitorowanie**: Statystyki i logi dla automatycznych uruchomień
- **Rate limiting**: Wbudowane opóźnienia chroniące API Sejmu

## Opcje konfiguracji

Wszystkie opcje konfiguracyjne znajdują się w `config.py`:

- `DEFAULT_TERM`: Domyślna kadencja (10)
- `REQUEST_DELAY`: Opóźnienie między zapytaniami (1 sekunda)
- `BASE_OUTPUT_DIR`: Katalog wyjściowy ("stenogramy_sejm")
- `REQUEST_TIMEOUT`: Timeout dla zapytań (30 sekund)

## API Sejmu RP

Program używa oficjalnego API Sejmu dostępnego pod adresem:

- https://api.sejm.gov.pl/

Szczegółowy opis przydatnych endpointów: [API.md](API.md)

### Wykorzystywane endpointy:

- `/sejm/term` - lista kadencji
- `/sejm/term{term}/proceedings` - lista posiedzeń
- `/sejm/term{term}/proceedings/{id}` - szczegóły posiedzenia
- `/sejm/term{term}/proceedings/{id}/{date}/transcripts` - lista wypowiedzi
- `/sejm/term{term}/proceedings/{id}/{date}/transcripts/pdf` - stenogram PDF
- `/sejm/term{term}/proceedings/{id}/{date}/transcripts/{num}` - wypowiedź HTML

## Przykłady

### Pobranie całej kadencji z wypowiedziami

```bash
python main.py -t 10 --statements -v --log-file kadencja_10.log
```

### Pobranie tylko konkretnych posiedzeń

```bash
python main.py -t 10 -p 1
python main.py -t 10 -p 15
python main.py -t 10 -p 23
```

### Sprawdzenie dostępnych kadencji i posiedzeń

```bash
python main.py --list-terms
python main.py -t 10 --summary
```

### Automatyczne uruchomienie (cron example)

```bash
# Codziennie o 22:00 - pobierz najnowsze stenogramy
0 22 * * * cd /path/to/SejmBot-scraper && python main.py -v --log-file "auto_$(date +\%Y\%m\%d).log"
```

## Logowanie i statystyki

Program automatycznie loguje wszystkie operacje i generuje szczegółowe statystyki:

### Poziomy logów:

- **INFO**: Podstawowe informacje o postępie
- **DEBUG**: Szczegółowe informacje (z opcją `-v`)
- **ERROR**: Błędy podczas pobierania
- **WARNING**: Ostrzeżenia o brakujących danych

### Statystyki końcowe:

```
📊 PODSUMOWANIE POBIERANIA KADENCJI 10
==================================================
Przetworzone posiedzenia: 25
Pominięte przyszłe posiedzenia: 3
Pobrane PDF-y:           45
Zapisane wypowiedzi:     1250
Błędy:                   0
==================================================
```

## Powiązane projekty

Pobrane stenogramy są następnie przetwarzane przez inne komponenty SejmBot w celu:

- Wykrywania fragmentów o potencjale humorystycznym
- Analizy AI pod kątem śmieszności (OpenAI/Claude)
- Generowania powiadomień mobilnych dla użytkowników końcowych

SejmBot-scraper może być również używany niezależnie przez każdego, kto potrzebuje dostępu do stenogramów Sejmu RP.

## Ograniczenia i uwagi

1. **Rate limiting**: Program ma wbudowane opóźnienia między zapytaniami (1 sekunda), aby nie przeciążać serwera API.

2. **Rozmiar danych**: Pełna kadencja może zajmować kilka GB przestrzeni dyskowej.

3. **Przyszłe posiedzenia**: Automatycznie pomija posiedzenia zaplanowane na przyszłość (stenogramy nie są jeszcze
   dostępne).

4. **Format HTML wypowiedzi**: Poszczególne wypowiedzi zawierają metadane i template. Pełna treść wymaga dodatkowych
   zapytań do API.

5. **Dostępność API**: Program zależy od dostępności oficjalnego API Sejmu.

## Licencja

Program wykorzystuje publiczne API Sejmu RP zgodnie z jego
regulaminem. [Oprogramowanie na licencji Apache 2.0](https://github.com/philornot/SejmBot-scraper/blob/main/LICENSE).