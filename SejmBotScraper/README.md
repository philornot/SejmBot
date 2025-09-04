# SejmBotScraper

Narzędzie do automatycznego pobierania stenogramów i danych posłów z Sejmu Rzeczypospolitej Polskiej za pomocą
oficjalnego API. Stworzony jako część projektu **SejmBot** — systemu wykrywającego śmieszne momenty z polskiego
parlamentu.

## Opis

SejmBot-scraper wykorzystuje oficjalne API Sejmu RP do pobierania:

### 📜 Stenogramy i wypowiedzi

- Stenogramów w formacie PDF z całych dni posiedzeń
- Poszczególnych wypowiedzi w formacie HTML
- Metadanych dotyczących posiedzeń i wypowiedzi

### 👥 Dane posłów (NOWOŚĆ!)

- Informacje o wszystkich posłach danej kadencji
- Oficjalne zdjęcia posłów
- Statystyki głosowań i aktywności
- Dane klubów parlamentarnych i ich logotypy

Program automatycznie organizuje pobrane pliki w przejrzystą strukturę folderów i jest przygotowany do integracji z
systemami automatyzacji.

## Struktura projektu

```
SejmBot-scraper/
├── main.py              # Główny plik uruchamiający (stenogramy)
├── mp_main.py           # CLI do pobierania posłów
├── sejm_api.py          # Komunikacja z API Sejmu
├── scraper.py           # Główna logika scrapowania stenogramów
├── mp_scraper.py        # Logika scrapowania posłów
├── file_manager.py      # Zarządzanie plikami i folderami
├── scheduler.py         # Automatyczny scheduler
├── config.py            # Konfiguracja programu
├── API.md               # Dokumentacja API Sejmu RP
├── requirements.txt     # Zależności Python
├── README.md            # Ta dokumentacja
└── .env.example         # Przykład konfiguracji środowiskowej
```

## Instalacja

1. **Sklonuj repozytorium**:

```bash
git clone https://github.com/philornot/SejmBot-scraper.git
cd SejmBot-scraper
```

2. **Zainstaluj zależności**:

```bash
pip install -r requirements.txt
```

3. **Skonfiguruj środowisko** (opcjonalnie):

```bash
cp .env.example .env
# Edytuj .env według potrzeb
```

## Funkcje

### 📜 Stenogramy

- **Inteligentne filtrowanie**: Automatycznie pomija duplikaty i przyszłe posiedzenia
- **Szczegółowe statystyki**: Raportuje postęp, błędy, pominięte posiedzenia
- **Metadane**: Zapisuje strukturalne informacje o posiedzeniach w JSON
- **Obsługa błędów**: Rozróżnia błędy rzeczywiste od normalnych braków danych

### 👥 Posłowie

- **Kompletne profile posłów**: Dane osobowe, zdjęcia, statystyki
- **Grupowanie**: Automatyczne grupowanie po klubach i województwach
- **Eksport danych**: JSON i CSV dla łatwego importu
- **Incremental updates**: Pobiera tylko nowe/zmienione dane

### 🤖 Automatyzacja

- **Production-ready**: Robust error handling, rate limiting, szczegółowe logowanie
- **Built-in scheduler**: Automatyczne pobieranie nowych danych
- **CLI z wieloma opcjami**: Elastyczne konfigurowanie pobierania
- **Cron compatibility**: Przystosowany do automatycznych uruchomień

## Użycie

### 📜 Stenogramy

#### Podstawowe użycie

```bash
# Pobierz całą 10. kadencję (tylko PDF-y)
python main.py

# Pobierz konkretną kadencję
python main.py -t 9

# Pobierz konkretne posiedzenie
python main.py -t 10 -p 15
```

#### Opcje pobierania

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

#### Opcje informacyjne

```bash
# Wyświetl dostępne kadencje
python main.py --list-terms

# Wyświetl podsumowanie posiedzeń danej kadencji
python main.py -t 10 --summary
```

### 👥 Posłowie

#### Podstawowe użycie

```bash
# Pobierz wszystkich posłów z 10. kadencji
python mp_main.py

# Pobierz posłów z 9. kadencji
python mp_main.py -t 9

# Pobierz konkretnego posła po ID
python mp_main.py --mp-id 123

# Pobierz tylko kluby parlamentarne
python mp_main.py --clubs-only
```

#### Opcje pobierania

```bash
# Pełne pobieranie (wszystko)
python mp_main.py --complete

# Bez zdjęć i statystyk (szybsze)
python mp_main.py --no-photos --no-stats

# Tylko podsumowanie (bez pobierania)
python mp_main.py --summary

# Z verbose logging
python mp_main.py -v --log-file mp_scraper.log
```

### 🤖 Automatyzacja

#### Scheduler (ciągły tryb)

```bash
# Uruchom scheduler dla bieżących stenogramów
python scheduler.py --continuous

# Jednorazowe sprawdzenie
python scheduler.py --once

# Status schedulera
python scheduler.py --status
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
    ├── posiedzenie_002_2023-11-20/
    │   └── ...
    └── poslowie/                      # NOWOŚĆ: Dane posłów
        ├── lista_poslow.json          # Pełna lista posłów
        ├── poslowie.csv               # Eksport CSV
        ├── podsumowanie_poslow.json   # Raport z grupowaniem
        ├── posel_001_Jan_Kowalski.json
        ├── posel_002_Anna_Nowak.json
        ├── zdjecia/
        │   ├── posel_001.jpg          # Zdjęcia posłów
        │   └── posel_002.png
        ├── statystyki_glosowan/
        │   ├── posel_001_statystyki.json
        │   └── posel_002_statystyki.json
        └── kluby/
            ├── lista_klubow.json
            ├── klub_01_Prawo_i_Sprawiedliwosc.json
            ├── klub_02_Platforma_Obywatelska.json
            ├── logo_01_Prawo_i_Sprawiedliwosc.png
            └── logo_02_Platforma_Obywatelska.png
```

## Automatyzacja

SejmBot-scraper jest przygotowany do integracji z systemami automatyzacji:

- **Kompatybilny z cron jobs**: Szczegółowe logi, return codes
- **Built-in scheduler**: Automatyczne pobieranie nowych stenogramów
- **Monitorowanie**: Statystyki i logi dla automatycznych uruchomień
- **Rate limiting**: Wbudowane opóźnienia chroniące API Sejmu

### Przykłady cron jobs

```bash
# Codziennie o 22:00 - pobierz najnowsze stenogramy
0 22 * * * cd /path/to/SejmBot-scraper && python main.py -v --log-file "auto_$(date +\%Y\%m\%d).log"

# Codziennie o 3:00 - sprawdź nowych posłów
0 3 * * * cd /path/to/SejmBot-scraper && python mp_main.py --complete -v --log-file "mp_auto_$(date +\%Y\%m\%d).log"

# Ciągły scheduler dla stenogramów
@reboot cd /path/to/SejmBot-scraper && python scheduler.py --continuous
```

## Opcje konfiguracji

Wszystkie opcje konfiguracyjne znajdują się w `config.py` i mogą być nadpisane przez plik `.env`:

### Podstawowe ustawienia

- `DEFAULT_TERM`: Domyślna kadencja (10)
- `REQUEST_DELAY`: Opóźnienie między zapytaniami (1 sekunda)
- `BASE_OUTPUT_DIR`: Katalog wyjściowy ("stenogramy_sejm")
- `REQUEST_TIMEOUT`: Timeout dla zapytań (30 sekund)

### Scheduler

- `SCHEDULER_INTERVAL`: Jak często sprawdzać nowe transkrypty (30 minut)
- `MAX_PROCEEDING_AGE`: Jak stare posiedzenia sprawdzać (7 dni)
- `ENABLE_NOTIFICATIONS`: Powiadomienia webhook (false)
- `NOTIFICATION_WEBHOOK`: URL webhooka (Slack, Discord, Teams)

### Logowanie

- `LOG_LEVEL`: Poziom logowania (INFO, DEBUG, WARNING, ERROR)
- `LOG_TO_FILE`: Zapisywanie logów do pliku (true)
- `LOG_FILE_MAX_SIZE_MB`: Maksymalny rozmiar pliku logu (50MB)

## API Sejmu RP

Program używa oficjalnego API Sejmu dostępnego pod adresem:

- https://api.sejm.gov.pl/

Szczegółowy opis przydatnych endpointów: [API.md](API.md)

### Wykorzystywane endpointy:

#### Stenogramy

- `/sejm/term` - lista kadencji
- `/sejm/term{term}/proceedings` - lista posiedzeń
- `/sejm/term{term}/proceedings/{id}` - szczegóły posiedzenia
- `/sejm/term{term}/proceedings/{id}/{date}/transcripts` - lista wypowiedzi
- `/sejm/term{term}/proceedings/{id}/{date}/transcripts/pdf` - stenogram PDF
- `/sejm/term{term}/proceedings/{id}/{date}/transcripts/{num}` - wypowiedź HTML

#### Posłowie

- `/sejm/term{term}/MP` - lista posłów
- `/sejm/term{term}/MP/{id}` - szczegóły posła
- `/sejm/term{term}/MP/{id}/photo` - zdjęcie posła
- `/sejm/term{term}/MP/{id}/votings/stats` - statystyki głosowań posła
- `/sejm/term{term}/clubs` - lista klubów parlamentarnych
- `/sejm/term{term}/clubs/{id}` - szczegóły klubu
- `/sejm/term{term}/clubs/{id}/logo` - logo klubu

## Przykłady

### Stenogramy

#### Pobranie całej kadencji z wypowiedziami

```bash
python main.py -t 10 --statements -v --log-file kadencja_10.log
```

#### Pobranie tylko konkretnych posiedzeń

```bash
python main.py -t 10 -p 1
python main.py -t 10 -p 15
python main.py -t 10 -p 23
```

#### Sprawdzenie dostępnych kadencji i posiedzeń

```bash
python main.py --list-terms
python main.py -t 10 --summary
```

### Posłowie

#### Pełne pobieranie danych o posłach

```bash
python mp_main.py -t 10 --complete -v --log-file mp_kadencja_10.log
```

#### Szybkie pobieranie bez mediów

```bash
python mp_main.py -t 10 --no-photos --no-stats
```

#### Monitoring konkretnego posła

```bash
python mp_main.py --mp-id 123 -v
```

### Łączone użycie

```bash
# Pobierz wszystko z danej kadencji
python main.py -t 10 --statements && python mp_main.py -t 10 --complete
```

## Logowanie i statystyki

Program automatycznie loguje wszystkie operacje i generuje szczegółowe statystyki:

### Poziomy logów:

- **INFO**: Podstawowe informacje o postępie
- **DEBUG**: Szczegółowe informacje (z opcją `-v`)
- **ERROR**: Błędy podczas pobierania
- **WARNING**: Ostrzeżenia o brakujących danych

### Statystyki końcowe - Stenogramy:

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

### Statystyki końcowe - Posłowie:

```
📊 PODSUMOWANIE POBIERANIA KADENCJI 10
============================================================
Pobrani posłowie:       460
Pobrane kluby:          8  
Pobrane zdjęcia:        458
Pobrane statystyki:     460
Błędy:                  2
============================================================
```

## Programowe użycie

### Stenogramy

```python
from scraper import SejmScraper

scraper = SejmScraper()

# Pobierz całą kadencję
stats = scraper.scrape_term(10, download_pdfs=True, download_statements=True)

# Pobierz konkretne posiedzenie
success = scraper.scrape_specific_proceeding(10, 15, True, True)

# Sprawdź dostępne kadencje
terms = scraper.get_available_terms()
```

### Posłowie

```python
from mp_scraper import MPScraper

mp_scraper = MPScraper()

# Pobierz wszystkich posłów
stats = mp_scraper.scrape_mps(10, download_photos=True, download_voting_stats=True)

# Pobierz tylko kluby
club_stats = mp_scraper.scrape_clubs(10)

# Pobierz konkretnego posła
success = mp_scraper.scrape_specific_mp(10, 123)

# Podsumowanie bez pobierania
summary = mp_scraper.get_mps_summary(10)
```

### Kombinowane

```python
from scraper import SejmScraper
from mp_scraper import MPScraper


# Kompleksowe pobieranie kadencji
def download_complete_term(term):
    # Stenogramy
    scraper = SejmScraper()
    transcript_stats = scraper.scrape_term(term, True, True)

    # Posłowie  
    mp_scraper = MPScraper()
    mp_stats = mp_scraper.scrape_complete_term_data(term)

    return {
        'transcripts': transcript_stats,
        'mps': mp_stats
    }


stats = download_complete_term(10)
```

## Powiązane projekty

Pobrane stenogramy i dane posłów są następnie przetwarzane przez inne komponenty SejmBot w celu:

- **Wykrywania fragmentów o potencjale humorystycznym**
- **Analizy AI pod kątem śmieszności** (OpenAI/Claude)
- **Generowania powiadomień mobilnych** dla użytkowników końcowych
- **Profilowania posłów** pod kątem generowania humoru
- **Statystyk regionalnych i klubowych** aktywności parlamentarnej

SejmBot-scraper może być również używany niezależnie przez każdego, kto potrzebuje dostępu do stenogramów i danych
posłów Sejmu RP.

## Ograniczenia i uwagi

1. **Rate limiting**: Program ma wbudowane opóźnienia między zapytaniami (1 sekunda), aby nie przeciążać serwera API.

2. **Rozmiar danych**:
    - Pełna kadencja stenogramów może zajmować kilka GB przestrzeni dyskowej
    - Dane posłów z zdjęciami to dodatkowe ~100-200MB na kadencję

3. **Przyszłe posiedzenia**: Automatycznie pomija posiedzenia zaplanowane na przyszłość (stenogramy nie są jeszcze
   dostępne).

4. **Format HTML wypowiedzi**: Poszczególne wypowiedzi zawierają metadane i template. Pełna treść wymaga dodatkowych
   zapytań do API.

5. **Dostępność API**: Program zależy od dostępności oficjalnego API Sejmu.

6. **Zdjęcia posłów**: Niektórzy posłowie mogą nie mieć zdjęć w systemie - to normalne zachowanie.

7. **Statystyki nowych posłów**: Dla bardzo nowych posłów statystyki głosowań mogą być niedostępne.

## Rozwiązywanie problemów

### Błędy pobierania

- Sprawdź połączenie internetowe
- Zweryfikuj dostępność API: `curl https://api.sejm.gov.pl/sejm/term`
- Zwiększ timeout w konfiguracji jeśli połączenie jest wolne

### Problemy z miejscem na dysku

- Użyj `--no-pdfs` dla stenogramów jeśli potrzebujesz tylko metadanych
- Użyj `--no-photos` dla posłów jeśli nie potrzebujesz zdjęć
- Regularnie archiwizuj stare dane

### Rate limiting

- Program automatycznie czeka między zapytaniami
- Nie uruchamiaj wielu instancji równocześnie
- W przypadku problemów zwiększ `REQUEST_DELAY` w konfiguracji

## Licencja

Program wykorzystuje publiczne API Sejmu RP zgodnie z jego regulaminem.

[Oprogramowanie na licencji Apache 2.0](https://github.com/philornot/SejmBot/blob/main/LICENSE)