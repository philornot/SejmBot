# SejmBotDetektor

Moduł odpowiedzialny za przygotowanie tekstu i ekstrakcję fragmentów do dalszej analizy AI.

Ten pakiet to aktualnie szkielet: CLI entrypoint, konfiguracja i miejsce na implementację przetwarzania.

Szybkie uruchomienie (venv zalecane):

```powershell
python -m SejmBotDetektor.main --help
python -m SejmBotDetektor.main --test-mode --max-statements 5
```

Co tu będzie się działo (w przyszłości):
- preprocessing (normalizacja, segmentacja)
- scoring na bazie słów kluczowych
- ekstrakcja fragmentów i serializacja wyników

Pliki:
- `config.py` — domyślne ustawienia detektora
- `main.py` — entrypoint CLI
