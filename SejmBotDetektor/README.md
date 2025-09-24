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

Funkcje preprocessing
---------------------

SejmBotDetektor zawiera moduł `preprocessing` z trzema podstawowymi funkcjami:

- `normalize_text(text: str) -> str`
	- Co robi: unescapuje encje HTML, usuwa nadmiarowe białe znaki, zamienia tekst na małe litery (zachowuje polskie znaki diakrytyczne) i zastępuje `&` słowem ` i `.
	- Zastosowanie: używaj przed dalszymi analizami (tokenizacja, scoring).

- `clean_html(html_content: str) -> str`
	- Co robi: usuwa bloki `<script>` i `<style>`, zamienia znacznik `<br>` i niektóre tagi blokowe na nowe linie, usuwa wszystkie tagi HTML, unescapuje encje i normalizuje odstępy.
	- Zastosowanie: konwersja treści wypowiedzi (HTML) do czystego tekstu.

- `split_into_sentences(text: str, max_chars: int = 500) -> List[str]`
	- Co robi: dzieli tekst na segmenty zdaniowe (heurystycznie po `.?!`), zapewniając, że każdy segment nie przekracza `max_chars`. Jeśli zdanie jest zbyt długie, dzieli po przecinkach lub na kawałki po słowach.
	- Zastosowanie: przygotowanie krótszych fragmentów do oceny (np. do API AI z limitem tokenów).

Przykład użycia (skrót):

```python
from SejmBotDetektor.preprocessing import clean_html, normalize_text, split_into_sentences

raw_html = '<p>Przykład wypowiedzi &amp; encja</p>'
text = clean_html(raw_html)
text = normalize_text(text)
segments = split_into_sentences(text, max_chars=200)
```

Uwagi i edge-cases
-------------------
- Funkcje stosują proste heurystyki (regex). Dla trudniejszych przypadków (skrótów, inicjałów, cytatów) rozważ użycie narzędzi NLP.
- `normalize_text` nie usuwa polskich znaków — to ważne dla poprawnej leksyki i dalszych analiz.
- `split_into_sentences` ma na celu wygenerować fragmenty maksymalnie krótkie; nie gwarantuje językowo idealnego podziału.

