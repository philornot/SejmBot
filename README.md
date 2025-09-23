# SejmBot — system do wykrywania zabawnych fragmentów z posiedzeń Sejmu

SejmBot to docelowo apka mobilna. Bot po każdym posiedzeniu sejmu RP wchodzi na stronę sejmu, pobiera najnowszy transkrypt posiedzenia w pdfie, zamienia go na tekst i ekstraktuje wypowiedzi łącząc je z ich autorami (i ich klubami parlamentarnymi), a następnie szuka w wypowiedziach słów kluczowych jak "żart”, "absurd" i inne (mam listę chyba około 150 słów, każde z odpowiednią wagą) które mogą wskazywać na to, że wypowiedź (jej fragment) jest śmieszny. (Na tym etapie jestem). Następnie na podstawie nagromadzenia tych słów kluczowych w wypowiedziach wybieramy 33 % najlepszych, a następnie je wysłamy do API OpenAI/Claude z zapytaniem: czy to jest śmieszne? Jeśli tak, to w ten sposób wyselekcjonowany śmiesny fragment z linkiem do pełnej wypowiedzi w formie wideo z wideorekordu posiedzenia jest wysłany do bazy danych, skąd jest przesyłany do aplikacji mobilnej. End user dostaje powiadomienie z wygenerowanym przez dane API nagłówkiem śmiesznej wypowiedzi (podsumowaniem jej np.), klika w powiadomienie i jest 10 % szans że się uśmiechnie pod nosem, i jego dzień będzie o 🤏 lepszy dzięki mnie.

## Cel projektu

SejmBot to zestaw narzędzi do pobierania stenogramów i wykrywania fragmentów wypowiedzi o potencjale humorystycznym.
Pipeline składa się z trzech głównych komponentów:

- SejmBotScraper — pobiera stenogramy i wypowiedzi z oficjalnego API Sejmu.
- SejmBotDetektor — analizuje teksty i wyodrębnia fragmenty potencjalnie zabawne.
- SejmBotAI (w planach) — dodatkowa analiza przez model AI (np. OpenAI/Claude) i selekcja wyników.

Repozytorium zawiera implementacje modułów oraz skrypty pomocnicze do lokalnego uruchomienia i integracji w pipeline.

## Szybka instalacja

1. Utwórz i aktywuj wirtualne środowisko w katalogu projektu:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

2. Zainstaluj zależności:

```powershell
pip install -r requirements.txt
```

3. (Opcjonalnie) Skonfiguruj wartości w `.env` lub w plikach konfiguracyjnych znajdujących się w katalogach `SejmBotScraper/config` i `SejmBotDetektor/config`.

## Uruchamianie

Przykładowe polecenia:

- Pobranie stenogramów (domyślnie zapis w katalogu, z którego uruchamiasz):

```powershell
python -m SejmBotScraper.main
```

- Hurtowe pobranie z pobieraniem treści wypowiedzi:

```powershell
python -m SejmBotScraper.main --bulk --fetch-full-statements --concurrent-downloads 4
```

## Architektura i flow

1. SejmBotScraper pobiera listę posiedzeń i dokumenty (PDF/HTML), zapisuje metadane i transkrypcje.
2. SejmBotDetektor przetwarza zapisaną zawartość, wyszukuje słowa kluczowe i generuje fragmenty z metadanymi.
3. W planach: SejmBotAI dokonuje oceny „śmieszności” fragmentów i przygotowuje finalne wyniki dla aplikacji mobilnej.

## Format danych wyjściowych

Transkrypty i wyniki detektora zapisujemy w formacie JSON. Przykładowe pliki i struktury:

- `info_posiedzenia.json` — metadane posiedzenia
- `transcripts/transkrypty_<YYYY-MM-DD>.json` — lista wypowiedzi (pole `text` oraz minimalne metadane)
- `detector/results_<timestamp>.json` — wyniki detektora z fragmentami i ocenami

Szczegółowy opis formatu `transkrypty_<YYYY-MM-DD>.json` znajduje się w `SejmBotScraper/README.md`.

## CLI i przydatne opcje SejmBotScraper

- `--bulk` — uruchamia hurtowe pobieranie.
- `--fetch-full-statements` — pobiera treść wypowiedzi (HTML -> tekst). Domyślnie wyłączone.
- `--concurrent-downloads N` — limit równoległości pobrań.
- `--output-dir PATH` — katalog wyjściowy.
- `--max-proceedings N` — do testów, ogranicza liczbę posiedzeń.
- `--log-file FILE` — zapis logów do pliku.

## Testy i uruchomienia lokalne

- Do szybkich testów użyj `--max-proceedings 1` i `--concurrent-downloads 1`.
- Uruchomienia planuj z aktywnym venv, odpowiednimi limitami równoległości i zapisem logów.

## Ograniczenia i uwagi

- Projekt wykorzystuje publiczne API Sejmu; dostępność API wpływa na działanie.
- Pełne pobranie i analiza całej kadencji może zajmować dużo miejsca i czasu.
- Nie wszystkie wypowiedzi mają łatwo dostępne treści; w takim przypadku pliki z transkryptami mogą nie powstać.

## Dalszy rozwój

SejmBotDetektor czeka w niedługim czasie remont generalny. Poza tym:

- Integracja z OpenAI/Anthropic API w celu selekcji fragmentów.
- Automatyzacja pipeline (scheduler, orkiestracja z backendem i bazą danych).
- Testy jednostkowe i schema validation dla plików wyjściowych.

## Licencja

Projekt stworzony w celach edukacyjnych i rozrywkowych.  
Wykorzystuje publiczne transkrypty z posiedzeń Sejmu RP.

[Oprogramowanie jest na licencji Apache 2.0.](https://github.com/philornot/SejmBot/blob/main/LICENSE)

---

#### ej aj?

tak, sejmbot jest rozwijany _przy pomocy_ chatbotów :> (dopóki działa to czemu nie?)\*
