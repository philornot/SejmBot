# SejmBot — Detektor śmiesznych momentów z polskiego parlamentu

## Basically:

SejmBot to docelowo apka mobilna. Bot po każdym posiedzeniu sejmu RP wchodzi na stronę sejmu, pobiera najnowszy
transkrypt posiedzenia w pdfie, zamienia go na tekst i ekstraktuje wypowiedzi łącząc je z ich autorami (i ich klubami
parlamentarnymi), a następnie szuka w wypowiedziach słów kluczowych jak "żart”, "absurd" i inne (mam listę chyba około
150 słów, każde z odpowiednią wagą) które mogą wskazywać na to, że wypowiedź (jej fragment) jest śmieszny. (Na tym
etapie jestem). Następnie na podstawie nagromadzenia tych słów kluczowych w wypowiedziach wybieramy 33 % najlepszych, a
następnie je wysłamy do API OpenAI/Claude z zapytaniem: czy to jest śmieszne? Jeśli tak, to w ten sposób
wyselekcjonowany śmiesny fragment z linkiem do pełnej wypowiedzi w formie wideo z wideorekordu posiedzenia jest wysłany
do bazy danych, skąd jest przesyłany do aplikacji mobilnej. End user dostaje powiadomienie z wygenerowanym przez dane
API nagłówkiem śmiesznej wypowiedzi (podsumowaniem jej np.), klika w powiadomienie i jest 10 % szans że się uśmiechnie
pod nosem, i jego dzień będzie o 🤏 lepszy dzięki mnie.

## Architektura systemu

### Pipeline przetwarzania:

1. **Automatyczne pobieranie** stenogramów z API Sejmu RP (SejmBotScraper)
2. **Detekcja fragmentów** ze słowami kluczowymi wskazującymi na humor (SejmBotDetektor)
3. **Analiza AI** najlepszych fragmentów (OpenAI/Claude API)
4. **Selekcja i linkowanie** z nagraniami wideo z posiedzeń
5. **Powiadomienia push** przez aplikację mobilną
6. **Happiness++** użytkowników końcowych

## Obecny etap rozwoju

**Aktualnie:** Etap 2 - System przetwarzania tekstu + Etap 3 - Automatyzacja scrapingu

### ✅ Zaimplementowane komponenty:

#### SejmBotScraper

- Zaawansowane pobieranie stenogramów z API Sejmu RP
- Inteligentne filtrowanie duplikatów i przyszłych posiedzeń
- Production-ready automation (cron-compatible)
- Szczegółowe statystyki i error handling

#### SejmBotDetektor

- Wczytuje pliki PDF z transkryptami Sejmu
- Wykrywa słowa kluczowe mogące wskazywać na śmieszność
- Wyodrębnia fragmenty z kontekstem
- Zapisuje metadane (mówca, posiedzenie, poziom pewności)
- Eksportuje wyniki do JSON/CSV

### 🔄 W trakcie rozwoju:

- **Scheduler/Cron integration** dla automatycznego pobierania
- **Pipeline orchestration** łączący scraper z detektorem

## Funkcjonalności SejmBotDetektora

### Główne możliwości

- **Analiza PDF:** Automatyczne wyciąganie tekstu z transkryptów
- **Wykrywanie słów kluczowych:** Ponad 30 słów wskazujących na humor/absurd
- **System oceniania:** Algorytm pewności (0.0-1.0) dla każdego fragmentu
- **Filtrowanie duplikatów:** Automatyczne usuwanie podobnych fragmentów
- **Eksport wyników:** JSON, CSV z pełnymi metadanymi
- **Tryb debugowania:** Szczegółowe logi procesu analizy

### Przykładowe słowa kluczowe

- **Wysokiej pewności:** śmiech, żart, bzdura, cyrk, gafa, wrzawa
- **Średniej pewności:** chaos, skandaliczny, awantura, oklaski
- **Niskiej pewności:** teatr, naprawdę, serio (wymagają kontekstu)

## Algorytm wykrywania

System używa wielokryterialnej analizy:

1. **Wyszukiwanie słów kluczowych** z wagami (1-3 punkty)
2. **Analiza kontekstu** — wykluczenie formalnych części
3. **Ocena długości** — preferowane fragmenty 20+ słów
4. **Bonus za różnorodność** — wiele różnych słów kluczowych
5. **Identyfikacja mówcy** — wyższy priorytet dla znanych polityków

## Przykłady konfiguracji detektora

### Restrykcyjne przetwarzanie (tylko najlepsze)

```python
pdf_path = "transkrypty_sejmu"
min_confidence = 0.6  # Wysoki próg pewności
max_fragments_per_file = 5  # Mało fragmentów z każdego pliku
max_total_fragments = 25  # Mały limit całkowity
```

### Obszerne przetwarzanie (więcej wyników)

```python
pdf_path = "transkrypty_sejmu"
min_confidence = 0.2  # Niski próg pewności
max_fragments_per_file = 50  # Dużo fragmentów z każdego pliku
max_total_fragments = 500  # Duży limit całkowity
```

## Przykłady użycia

### SejmBotScraper - Pobieranie stenogramów

```bash
# Pobierz całą kadencję z wypowiedziami
python scraper/main.py -t 10 --statements -v --log-file kadencja_10.log

# Pobierz konkretne posiedzenia
python scraper/main.py -t 10 -p 15

# Sprawdź dostępne kadencje
python scraper/main.py --list-terms
```

### SejmBotDetektor - Analiza humoru

```python
from SejmBotDetektor.detector import FragmentDetector

detector = FragmentDetector(debug=True)
results = detector.process_folder(
    "stenogramy_sejm/kadencja_10",
    min_confidence=0.3,
    max_total_fragments=100
)
```

## Statystyki i metryki

System generuje automatyczne statystyki:

- Łączna liczba znalezionych fragmentów
- Średnia/min/max pewność
- Top 5 najaktywniejszych mówców
- Najczęściej występujące słowa kluczowe
- Rozkład pewności fragmentów

## Przyszłe etapy

- [ ] **Etap 4:** Integracja z API OpenAI dla lepszej analizy humoru
- [ ] **Etap 5:** Linkowanie fragmentów z nagraniami wideo z posiedzeń
- [ ] **Etap 6:** Backend i baza danych (Firebase)
- [ ] **Etap 7:** Aplikacja mobilna (Kotlin)
- [ ] **Etap 8:** System powiadomień push
- [ ] **Etap 9:** Deployment i automatyzacja
- [ ] **Etap 10:** Monitoring jakości i user feedback

## Komponenty systemu

### 🔧 SejmBotScraper

**Status:** Production ready  
**Funkcja:** Automatyczne pobieranie stenogramów z API Sejmu RP  
**Repo:** [SejmBot-scraper](https://github.com/philornot/SejmBot-scraper)

### 🎭 SejmBotDetektor

**Status:** Zaimplementowany  
**Funkcja:** Wykrywanie potencjalnie śmiesznych fragmentów  
**Lokalizacja:** `SejmBotDetektor/` w tym repo

### 🤖 SejmBotAI

**Status:** Planowany  
**Funkcja:** AI analysis śmieszności fragmentów (OpenAI/Claude)

### 📱 SejmBotMobile

**Status:** Planowany  
**Funkcja:** Aplikacja mobilna z powiadomieniami push

## Format wyjściowy

### JSON z wynikami detektora

```json
{
  "summary": {
    "total_files": 5,
    "total_fragments": 47,
    "files_processed": [
      "plik1.pdf",
      "plik2.pdf",
      ...
    ]
  },
  "files": {
    "plik1.pdf": {
      "fragment_count": 12,
      "avg_confidence": 0.65,
      "fragments": [
        ...
      ]
    }
  }
}
```

## Konfiguracja i rozszerzenia

### Dodawanie słów kluczowych

```python
from SejmBotDetektor.config.keywords import KeywordsConfig

KeywordsConfig.add_funny_keyword("nowe_słowo", weight=2)
KeywordsConfig.add_exclude_keyword("słowo_do_wykluczenia")
```

### Dostosowywanie wzorców mówców

W [`keywords.py`](https://github.com/philornot/SejmBot/blob/main/SejmBotDetektor/config/keywords.py) w
`SPEAKER_PATTERNS` - dodaj nowy wzorzec dla nietypowych formatów.

## Technologie

- **Python 3.8+** - główny język
- **Requests** - API communication
- **PyPDF2/pdfplumber** - PDF processing
- **pathlib** - file management
- **JSON/CSV** - data export
- **Logging** - comprehensive monitoring

## Limitacje

- **SejmBotScraper:** Zależy od dostępności API Sejmu RP
- **SejmBotDetektor:** Maksymalnie `max_total_fragments` fragmentów w wyniku
- **Przetwarzanie:** Duże foldery wymagają czasu na analizę
- **PDF:** Każdy plik musi być prawidłowy i zawierać tekst

## Licencja

Projekt stworzony w celach edukacyjnych i rozrywkowych.  
Wykorzystuje publiczne transkrypty z posiedzeń Sejmu RP.

[Oprogramowanie jest na licencji MIT.](https://github.com/philornot/SejmBot/blob/main/LICENSE)

---

#### ej aj?

tak, sejmbot jest rozwijany przy pomocy chatbotów :> (dopóki działa to czemu nie?)
