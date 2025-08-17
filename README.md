# SejmBot - Detektor śmiesznych momentów z polskiego parlamentu

**SejmBot** to system do automatycznego wykrywania humorystycznych i absurdalnych fragmentów z posiedzeń Sejmu RP.
Projekt analizuje transkrypty parlamentarne w poszukiwaniu zabawnych wypowiedzi polityków, wykorzystując algorytm oparty
na słowach kluczowych.

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
3. ✅ Wyodrębnia fragmenty z kontekstem (domyślnie ±50 słów)
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

### Konfiguracja parametrów

```python
# W pliku main_refactored.py
min_confidence = 0.4  # Próg pewności (0.0-1.0)
max_fragments = 20  # Max liczba wyników  
context_before = 30  # Słowa przed kluczowym
context_after = 30  # Słowa po kluczowym
```

## Algorytm wykrywania

System używa wielokryterialnej analizy:

1. **Wyszukiwanie słów kluczowych** z wagami (1-3 punkty)
2. **Analiza kontekstu** - wykluczenie formalnych części
3. **Ocena długości** - preferowane fragmenty 20+ słów
4. **Bonus za różnorodność** - wiele różnych słów kluczowych
5. **Identyfikacja mówcy** - wyższy priorytet dla znanych polityków

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

### JSON

```json
{
  "text": "Fragment wypowiedzi...",
  "speaker": "Jan Kowalski",
  "meeting_info": "15. posiedzenie Sejmu X kadencji",
  "keywords_found": [
    "śmiech",
    "cyrk"
  ],
  "confidence_score": 0.85,
  "timestamp": "2024-01-15T10:30:00"
}
```

### CSV

Kolumny: speaker, confidence_score, keywords_found, text_preview, meeting_info

## 📄 Licencja

Projekt stworzony w celach edukacyjnych i rozrywkowych.
Wykorzystuje publiczne transkrypty z posiedzeń Sejmu RP.

[Oprogramowanie jest na licencji MIT.](https://github.com/philornot/SejmBot/blob/main/LICENSE)


### ej aj?
tak, sejmbot jest rozwijany przy pomocy chatbotów :> (dopóki działa to czemu nie?)