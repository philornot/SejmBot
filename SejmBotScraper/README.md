# SejmBotScraper

Narzędzie do automatycznego pobierania stenogramów i danych posłów z Sejmu Rzeczypospolitej Polskiej za pomocą
oficjalnego API. Stworzony jako część projektu **SejmBot** — systemu wykrywającego śmieszne momenty z polskiego
parlamentu.

## Szybkie instrukcje

- Pracuj w wirtualnym środowisku (venv).

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

- Uruchomienie podstawowe (pobiera listę posiedzeń i PDFy):

```powershell
python -m SejmBotScraper.main
```

- Tryb produkcyjny — hurtowe pobieranie z opcją pobierania treści wypowiedzi:

```powershell
python -m SejmBotScraper.main --bulk --fetch-full-statements --concurrent-downloads 4
```

- Pobranie konkretnej kadencji i posiedzenia:

```powershell
python -m SejmBotScraper.main -t 10 -p 1 --fetch-full-statements
```

Jeśli chcesz, aby pliki zostały zapisane w katalogu, z którego uruchamiasz polecenie, nie podawaj parametru --output-dir
(to jest domyślne zachowanie). Możesz też jawnie wskazać katalog wyjściowy:

```powershell
python -m SejmBotScraper.main --bulk --output-dir C:\sciezka\do\wyjscia
```

## Ważne flagi CLI

- `--bulk` — tryb produkcyjny, pobiera zakres danych (hurtowo).
- `--fetch-full-statements` — pobiera pełną treść wypowiedzi (HTML -> tekst). Domyślnie wyłączone, żeby oszczędzać zasoby.
- `--concurrent-downloads N` — liczba równoległych pobrań (domyślnie: z ustawień).
- `--output-dir PATH` — katalog do zapisu danych; domyślnie katalog bieżący (CWD) lub wartość z konfiguracji.
- `--ignore-venv` — uruchom, nawet jeżeli nie wykryto aktywnego venv (zalecane: używać venv).
- `-v` / `--verbose` — poziom logów DEBUG.

## Struktura wyjściowa

Domyślny układ (przykład):

```
./kadencja_<N>/
    posiedzenie_<NNN>_<YYYY-MM-DD>/
        info_posiedzenia.json
        transcripts/
            transkrypty_<YYYY-MM-DD>.json
        transcripts_pdf/
            <plik>.pdf
```

Pliki są zapisywane atomowo tam, gdzie to możliwe (najpierw zapis tymczasowy, potem rename).

## Format pliku transkrypty\_<YYYY-MM-DD>.json

Pliki z transkryptami są zoptymalizowane pod kątem dalszej analizy automatycznej. Najważniejsze pola:

- metadata

  - kadencja: numer kadencji
  - posiedzenie_id: identyfikator posiedzenia
  - date: data posiedzenia
  - generated_at: znacznik czasu wygenerowania pliku
  - statements_count: liczba zapisanych wypowiedzi

- statements: lista obiektów
  - num: numer wypowiedzi lub indeks
  - speaker: { name, id (opcjonalnie), is_mp (bool), club (opcjonalnie) }
  - text: czysty tekst wypowiedzi (to, czego potrzebuje detektor)
  - start_time: opcjonalny znacznik rozpoczęcia
  - end_time: opcjonalny znacznik zakończenia
  - duration_seconds: opcjonalna długość wypowiedzi
  - original: oryginalny, surowy fragment (zachowany dla śledzenia źródła)

Jeśli pobieranie treści jest wyłączone lub nie znaleziono treści, plik nie zostanie utworzony.

## Logowanie i monitoring

Logi są zapisywane na poziomie INFO domyślnie. Można przełączyć na DEBUG flagą `-v`. Aby zapisać logi do pliku, użyj
opcji `--log-file nazwa.log`.

Po zakończeniu hurtowego pobierania program wypisuje krótkie statystyki (liczba posiedzeń, liczba wypowiedzi, liczba
pobranych treści, błędy).

## Przydatne wskazówki

- Do szybkich testów użyj `--max-proceedings 1` i małej liczby wypowiedzi (`--concurrent-downloads 1`) aby zweryfikować
  konfigurację i strukturę zapisów.
- Jeśli planujesz produkcyjne uruchomienia w harmonogramie (cron/Task Scheduler), upewnij się, że używasz venv i
  przekazujesz pełne ścieżki w `--output-dir` i `--log-file`.

## Licencja

Kod źródłowy jest objęty licencją Apache 2.0 (plik [LICENSE](https://github.com/philornot/SejmBot/blob/main/LICENSE) w repozytorium).
