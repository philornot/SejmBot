# SejmBot — Detektor śmiesznych momentów z polskiego parlamentu

## Basically:
SejmBot to docelowo apka mobilna. Bot po każdym posiedzeniu sejmu RP wchodzi na stronę sejmu, pobiera najnowszy transkrypt posiedzenia w pdfie, zamienia go na tekst i ekstraktuje wypowiedzi łącząc je z ich autorami (i ich klubami parlamentarnymi), a następnie szuka w wypowiedziach słów kluczowych jak "żart”, "absurd" i inne (mam listę chyba około 150 słów, każde z odpowiednią wagą) które mogą wskazywać na to, że wypowiedź (jej fragment) jest śmieszny. (Na tym etapie jestem). Następnie na podstawie nagromadzenia tych słów kluczowych w wypowiedziach wybieramy 33 % najlepszych, a następnie je wysłamy do API OpenAI/Claude z zapytaniem: czy to jest śmieszne? Jeśli tak, to w ten sposób wyselekcjonowany śmiesny fragment z linkiem do pełnej wypowiedzi w formie wideo z wideorekordu posiedzenia jest wysłany do bazy danych, skąd jest przesyłany do aplikacji mobilnej. End user dostaje powiadomienie z wygenerowanym przez dane API nagłówkiem śmiesznej wypowiedzi (podsumowaniem jej np.), klika w powiadomienie i jest 10 % szans że się uśmiechnie pod nosem, i jego dzień będzie o 🤏 lepszy dzięki mnie.

### Cel projektu

Głównym celem jest stworzenie kompletnego systemu, który:

- Automatycznie pobiera transkrypty z posiedzeń Sejmu
- Analizuje je pod kątem humoru i absurdalności
- Przesyła powiadomienia push z najciekawszymi fragmentami
- Udostępnia je użytkownikom poprzez aplikację mobilną

## Obecny etap rozwoju

**Aktualnie:** Etap 2 - System przetwarzania tekstu

Zaimplementowany został podstawowy detektor fragmentów, który:

1. ✅ Wczytuje pliki PDF z transkryptami Sejmu
2. ✅ Wykrywa słowa kluczowe mogące wskazywać na śmieszność
3. ✅ Wyodrębnia fragmenty z kontekstem
4. ✅ Zapisuje metadane (mówca, posiedzenie, poziom pewności)
5. ✅ Eksportuje wyniki do JSON/CSV

## Funkcjonalności

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

## Przykłady konfiguracji

### Restrykcyjne przetwarzanie (tylko najlepsze)
```python
pdf_path = "transkrypty_sejmu"
min_confidence = 0.6           # Wysoki próg pewności
max_fragments_per_file = 5     # Mało fragmentów z każdego pliku
max_total_fragments = 25       # Mały limit całkowity
```

### Obszerne przetwarzanie (więcej wyników)
```python
pdf_path = "transkrypty_sejmu"
min_confidence = 0.2           # Niski próg pewności
max_fragments_per_file = 50    # Dużo fragmentów z każdego pliku
max_total_fragments = 500      # Duży limit całkowity
```

### Zbalansowane przetwarzanie
```python
pdf_path = "transkrypty"
min_confidence = 0.3
max_fragments_per_file = 20
max_total_fragments = 100
```

## Algorytm wykrywania

System używa wielokryterialnej analizy:

1. **Wyszukiwanie słów kluczowych** z wagami (1-3 punkty)
2. **Analiza kontekstu** — wykluczenie formalnych części
3. **Ocena długości** — preferowane fragmenty 20+ słów
4. **Bonus za różnorodność** — wiele różnych słów kluczowych
5. **Identyfikacja mówcy** — wyższy priorytet dla znanych polityków

## Przyszłe etapy

- [ ] **Etap 3:** Bot do automatycznego pobierania transkryptów
- [ ] **Etap 4:** Integracja z API OpenAI dla lepszej analizy humoru
- [ ] **Etap 5:** Backend i baza danych (Supabase)
- [ ] **Etap 6:** Aplikacja mobilna (Flutter/React Native)
- [ ] **Etap 7:** System powiadomień push
- [ ] **Etap 8:** Deployment i automatyzacja

## Konfiguracja i rozszerzenia

### Dodawanie słów kluczowych i wykluczenia
Zmodyfikuj odpowiednio `FUNNY_WORDS` i `EXCLUDE_KEYWORDS` w [`SejmBotDetektor/config/keywords.py`](https://github.com/philornot/SejmBot/blob/main/SejmBotDetektor/config/keywords.py).

Lub:
```python
from SejmBotDetektor.config.keywords import KeywordsConfig

KeywordsConfig.add_funny_keyword("nowe_słowo", weight=2)
KeywordsConfig.add_exclude_keyword("słowo_do_wykluczenia")
```

### Dostosowywanie wzorców mówców

W [keywords.py w `SPEAKER_PATTERNS`](https://github.com/philornot/SejmBot/blob/main/SejmBotDetektor/config/keywords.py) - dodaj nowy wzorzec dla nietypowych formatów


## Statystyki i metryki

System generuje automatyczne statystyki:

- Łączna liczba znalezionych fragmentów
- Średnia/min/max pewność
- Top 5 najaktywniejszych mówców
- Najczęściej występujące słowa kluczowe
- Rozkład pewności fragmentów

## Debug

Włączenie trybu debug:

```python
detector = FragmentDetector(debug=True)
```

Zapewnia szczegółowe logi:

- Proces wczytywania PDF
- Wykrywanie słów kluczowych
- Obliczenia pewności
- Powody odrzucenia fragmentów

## Format wyjściowy

### JSON z wynikami z folderu

```json
{
  "summary": {
    "total_files": 5,
    "total_fragments": 47,
    "files_processed": ["plik1.pdf", "plik2.pdf", ...]
  },
  "files": {
    "plik1.pdf": {
      "fragment_count": 12,
      "avg_confidence": 0.65,
      "fragments": [...]
    }
  }
}
```

### CSV

Kolumny: source_file, speaker, confidence_score, keywords_found, text_preview, meeting_info

## Limitacje

* Maksymalnie `max_total_fragments` fragmentów w końcowym wyniku
* Fragmenty są wybierane według najwyższej pewności
* Bardzo duże foldery mogą wymagać czasu na przetworzenie
* Każdy plik PDF musi być prawidłowy i zawierać tekst

## Licencja

Projekt stworzony w celach edukacyjnych i rozrywkowych.
Wykorzystuje publiczne transkrypty z posiedzeń Sejmu RP.

[Oprogramowanie jest na licencji MIT.](https://github.com/philornot/SejmBot/blob/main/LICENSE)

---
#### ej aj?
tak, sejmbot jest rozwijany przy pomocy chatbotów :> (dopóki działa to czemu nie?)