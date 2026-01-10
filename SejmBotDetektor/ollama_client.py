"""
Używa lokalnego Ollama LLM lub zewnętrznych API (Claude/OpenAI)
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List

import requests

logger = logging.getLogger(__name__)


class HumorCategory(Enum):
    """Kategorie humoru w wypowiedziach."""
    ABSURD = "absurd"
    JOKE = "żart"
    IRONY = "ironia"
    GAFFE = "gafa"
    EXAGGERATION = "przesada"
    NONE = "brak"


@dataclass
class AnalysisResult:
    """Wynik analizy wypowiedzi."""
    is_funny: bool
    confidence: float  # 0.0 - 1.0
    reason: str
    category: HumorCategory
    raw_response: str = ""

    def to_dict(self) -> Dict:
        """Konwertuje do słownika."""
        return {
            'is_funny': self.is_funny,
            'confidence': self.confidence,
            'reason': self.reason,
            'category': self.category.value,
            'raw_response': self.raw_response
        }


class OllamaClient:
    """
    Klient dla lokalnego Ollama LLM.

    Analizuje wypowiedzi sejmowe pod kątem potencjału humorystycznego.
    Używa lokalnego modelu językowego zamiast płatnych API.

    Examples:
        >>> client = OllamaClient(model="llama3.1:8b")
        >>> if client.health_check():
        ...     result = client.is_statement_funny("Budżet jest abstrakcyjny")
        ...     print(f"Śmieszne: {result.is_funny}, Pewność: {result.confidence:.0%}")
    """

    def __init__(self,
                 base_url: str = "http://localhost:11434",
                 model: str = "speakleash/bielik-7b-instruct-v0.1-gguf",
                 timeout: int = 120):
        """
        Inicjalizuje klienta Ollama.

        Args:
            base_url: URL serwera Ollama
            model: Nazwa modelu do użycia (llama3.1:8b, bielik:7b, etc.)
            timeout: Timeout dla requestów w sekundach
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout

        # Statystyki
        self.stats = {
            'total_analyzed': 0,
            'funny_found': 0,
            'errors': 0,
            'avg_confidence': 0.0
        }

        logger.info(f"Zainicjalizowano OllamaClient: {model} @ {base_url}")

    def health_check(self) -> bool:
        """
        Sprawdza czy Ollama działa i czy model jest dostępny.

        Returns:
            True jeśli wszystko OK, False w przeciwnym razie
        """
        try:
            # Sprawdź czy serwer odpowiada
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            response.raise_for_status()

            tags_data = response.json()
            models = tags_data.get('models', [])

            # Sprawdź czy nasz model jest dostępny
            model_names = [m.get('name', '') for m in models]

            if not any(self.model in name for name in model_names):
                logger.error(f"Model {self.model} nie jest zainstalowany!")
                logger.info(f"Dostępne modele: {model_names}")
                logger.info(f"Zainstaluj przez: ollama pull {self.model}")
                return False

            logger.info(f"✓ Ollama działa, model {self.model} dostępny")
            return True

        except requests.exceptions.ConnectionError:
            logger.error(f"Nie można połączyć z Ollama na {self.base_url}")
            logger.info("Sprawdź czy Ollama działa: ollama serve")
            return False
        except Exception as e:
            logger.error(f"Błąd health check: {e}")
            return False

    def is_statement_funny(self,
                           text: str,
                           context: Optional[Dict] = None) -> AnalysisResult:
        """
        Analizuje czy wypowiedź jest śmieszna.

        Args:
            text: Tekst wypowiedzi do analizy (max 1000 znaków dla szybkości)
            context: Dodatkowy kontekst - słownik z polami:
                    - speaker: imię i nazwisko mówcy
                    - club: klub parlamentarny
                    - date: data wypowiedzi
                    - proceeding: numer posiedzenia

        Returns:
            AnalysisResult z oceną śmieszności
        """
        # Walidacja
        if not text or len(text.strip()) < 20:
            return AnalysisResult(
                is_funny=False,
                confidence=0.0,
                reason="Wypowiedź za krótka",
                category=HumorCategory.NONE
            )

        # Ogranicz długość dla szybkości
        text_limited = text[:1000]

        # Zbuduj prompt
        prompt = self._create_prompt(text_limited, context)

        try:
            # Wywołaj Ollama API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Niższa = bardziej konserwatywna ocena
                        "top_p": 0.9,
                        "num_predict": 200  # Max długość odpowiedzi
                    }
                },
                timeout=self.timeout
            )

            response.raise_for_status()
            result_json = response.json()

            # Parse odpowiedzi
            model_response = result_json.get('response', '')
            analysis = self._parse_model_response(model_response)

            # Aktualizuj statystyki
            self.stats['total_analyzed'] += 1
            if analysis.is_funny:
                self.stats['funny_found'] += 1

            # Oblicz średnią pewność
            total = self.stats['total_analyzed']
            avg = self.stats['avg_confidence']
            self.stats['avg_confidence'] = (avg * (total - 1) + analysis.confidence) / total

            return analysis

        except requests.exceptions.Timeout:
            logger.error(f"Timeout analizy wypowiedzi (>{self.timeout}s)")
            self.stats['errors'] += 1
            return AnalysisResult(
                is_funny=False,
                confidence=0.0,
                reason=f"Timeout po {self.timeout}s",
                category=HumorCategory.NONE
            )
        except Exception as e:
            logger.error(f"Błąd analizy: {e}")
            self.stats['errors'] += 1
            return AnalysisResult(
                is_funny=False,
                confidence=0.0,
                reason=f"Błąd: {str(e)[:100]}",
                category=HumorCategory.NONE
            )

    def _create_prompt(self, text: str, context: Optional[Dict]) -> str:
        """
        Tworzy prompt dla modelu LLM — uproszczony dla Bielika.
        """
        prompt = """Oceń czy poniższa wypowiedź z polskiego Sejmu jest śmieszna.

WYPOWIEDŹ:
{text}

Oceń według kryteriów:
- ABSURD: logiczne niespójności, paradoksy
- ŻART: celowy humor, dowcip
- IRONIA: sarkazm, drwina
- GAFA: przypadkowa pomyłka językowa
- PRZESADA: nadmierna hiperbolizacja

ODPOWIEDZ DOKŁADNIE W TYM FORMACIE (niżej przykłady):
ŚMIESZNE: TAK
PEWNOŚĆ: 75%
KATEGORIA: absurd
POWÓD: tutaj podaj krótkie uzasadnienie po polsku

LUB:

ŚMIESZNE: NIE
PEWNOŚĆ: 90%
KATEGORIA: brak
POWÓD: tutaj podaj krótkie uzasadnienie po polsku

Twoja ocena:""".replace('{text}', text[:800])  # Limit dla szybkości

        return prompt

    def _parse_model_response(self, response: str) -> AnalysisResult:
        """
        Parsuje odpowiedź modelu do struktury AnalysisResult.

        Obsługuje różne warianty odpowiedzi i błędy parsowania.
        """
        result = AnalysisResult(
            is_funny=False,
            confidence=0.0,
            reason='Brak odpowiedzi',
            category=HumorCategory.NONE,
            raw_response=response
        )

        if not response or len(response.strip()) < 10:
            return result

        try:
            lines = response.strip().split('\n')

            for line in lines:
                line = line.strip()

                # Parse ŚMIESZNE
                if any(keyword in line.upper() for keyword in ['ŚMIESZNE:', 'SMIESZ', 'FUNNY:']):
                    result.is_funny = any(word in line.upper() for word in ['TAK', 'YES', 'PRAWDA', 'TRUE'])

                # Parse PEWNOŚĆ
                elif any(keyword in line.upper() for keyword in ['PEWNOŚĆ:', 'PEWNOSC:', 'CONFIDENCE:']):
                    import re
                    # Wyciągnij liczbę (np. "75%" -> 75)
                    match = re.search(r'(\d+)', line)
                    if match:
                        confidence_val = float(match.group(1))
                        # Normalizuj do 0.0-1.0
                        result.confidence = min(confidence_val / 100.0, 1.0)

                # Parse KATEGORIA
                elif any(keyword in line.upper() for keyword in ['KATEGORIA:', 'CATEGORY:']):
                    category_text = line.split(':', 1)[1].strip().lower()

                    # Mapuj na enum
                    if 'absurd' in category_text:
                        result.category = HumorCategory.ABSURD
                    elif 'żart' in category_text or 'zart' in category_text or 'joke' in category_text:
                        result.category = HumorCategory.JOKE
                    elif 'ironi' in category_text:
                        result.category = HumorCategory.IRONY
                    elif 'gaf' in category_text:
                        result.category = HumorCategory.GAFFE
                    elif 'przesad' in category_text or 'exagger' in category_text:
                        result.category = HumorCategory.EXAGGERATION
                    else:
                        result.category = HumorCategory.NONE

                # Parse POWÓD
                elif any(keyword in line.upper() for keyword in ['POWÓD:', 'POWOD:', 'REASON:']):
                    result.reason = line.split(':', 1)[1].strip()

            # Walidacja - jeśli brak pewności ale jest funny, ustaw domyślną
            if result.is_funny and result.confidence == 0.0:
                result.confidence = 0.5

            # Jeśli brak powodu, wygeneruj domyślny
            if not result.reason or result.reason == 'Brak odpowiedzi':
                if result.is_funny:
                    result.reason = f"Model rozpoznał element {result.category.value}"
                else:
                    result.reason = "Brak wyraźnych elementów humorystycznych"

            logger.debug(f"Analiza: funny={result.is_funny}, "
                         f"conf={result.confidence:.2f}, "
                         f"cat={result.category.value}")

        except Exception as e:
            logger.error(f"Błąd parsowania odpowiedzi: {e}")
            logger.debug(f"Raw response: {response[:200]}")

        return result

    def analyze_batch(self,
                      statements: List[Dict],
                      threshold: float = 0.6,
                      max_statements: Optional[int] = None) -> List[Dict]:
        """
        Analizuje wiele wypowiedzi na raz.

        Args:
            statements: Lista wypowiedzi do analizy. Każda wypowiedź to dict z:
                       - 'text': tekst wypowiedzi (wymagane)
                       - 'speaker': dict z danymi mówcy (opcjonalne)
                       - 'metadata': dodatkowe metadane (opcjonalne)
            threshold: Minimalny próg pewności (0.0-1.0) dla filtrowania
            max_statements: Maksymalna liczba wypowiedzi do analizy (None = wszystkie)

        Returns:
            Lista wypowiedzi które przeszły próg śmieszności, posortowane wg pewności
        """
        funny_statements = []

        # Ogranicz jeśli potrzeba
        to_analyze = statements[:max_statements] if max_statements else statements

        logger.info(f"Rozpoczynam analizę {len(to_analyze)} wypowiedzi "
                    f"(próg pewności: {threshold:.0%})")

        for i, stmt in enumerate(to_analyze, 1):
            # Progress log co 10 wypowiedzi
            if i % 10 == 0:
                logger.info(f"Postęp: {i}/{len(to_analyze)} "
                            f"({len(funny_statements)} śmiesznych)")

            # Wyciągnij tekst
            text = stmt.get('text', '')
            if not text or len(text.strip()) < 20:
                continue

            # Zbuduj kontekst
            context = {}
            if 'speaker' in stmt and isinstance(stmt['speaker'], dict):
                context['speaker'] = stmt['speaker'].get('name')
                context['club'] = stmt['speaker'].get('club')

            if 'metadata' in stmt and isinstance(stmt['metadata'], dict):
                context.update({
                    'date': stmt['metadata'].get('date'),
                    'proceeding': stmt['metadata'].get('proceeding_id')
                })

            # Analizuj
            analysis = self.is_statement_funny(text, context)

            # Dodaj wynik do wypowiedzi
            stmt['ai_analysis'] = analysis.to_dict()

            # Jeśli przekracza próg - dodaj do wyników
            if analysis.is_funny and analysis.confidence >= threshold:
                funny_statements.append(stmt)
                logger.info(f"✓ Znaleziono śmieszną wypowiedź! "
                            f"Pewność: {analysis.confidence:.0%}, "
                            f"Kategoria: {analysis.category.value}")
                logger.debug(f"  Powód: {analysis.reason}")
                logger.debug(f"  Fragment: {text[:100]}...")

        # Sortuj wg pewności (malejąco)
        funny_statements.sort(
            key=lambda s: s['ai_analysis']['confidence'],
            reverse=True
        )

        logger.info(f"Znaleziono {len(funny_statements)} śmiesznych wypowiedzi "
                    f"z {len(to_analyze)} przeanalizowanych "
                    f"({len(funny_statements) / len(to_analyze) * 100:.1f}%)")

        return funny_statements

    def get_stats(self) -> Dict:
        """
        Zwraca statystyki analizy.

        Returns:
            Słownik ze statystykami:
            - total_analyzed: łączna liczba przeanalizowanych
            - funny_found: liczba śmiesznych znalezionych
            - funny_rate: procent śmiesznych
            - avg_confidence: średnia pewność
            - errors: liczba błędów
        """
        total = self.stats['total_analyzed']
        funny = self.stats['funny_found']

        return {
            'total_analyzed': total,
            'funny_found': funny,
            'funny_rate': (funny / total * 100) if total > 0 else 0.0,
            'avg_confidence': self.stats['avg_confidence'],
            'errors': self.stats['errors'],
            'model': self.model
        }

    def reset_stats(self):
        """Resetuje statystyki."""
        self.stats = {
            'total_analyzed': 0,
            'funny_found': 0,
            'errors': 0,
            'avg_confidence': 0.0
        }


# Funkcje pomocnicze dla łatwego użycia

def quick_analyze(text: str,
                  model: str = "llama3.1:8b",
                  threshold: float = 0.6) -> Dict:
    """
    Szybka analiza pojedynczej wypowiedzi.

    Args:
        text: Tekst do analizy
        model: Model Ollama do użycia
        threshold: Minimalny próg pewności

    Returns:
        Słownik z wynikami lub None jeśli błąd

    Examples:
        >>> result = quick_analyze("Budżet jest abstrakcyjny")
        >>> if result and result['is_funny']:
        ...     print(f"Śmieszne! Pewność: {result['confidence']:.0%}")
    """
    client = OllamaClient(model=model)

    if not client.health_check():
        logger.error("Ollama niedostępny")
        return None

    analysis = client.is_statement_funny(text)

    result = analysis.to_dict()
    result['passes_threshold'] = (
            analysis.is_funny and analysis.confidence >= threshold
    )

    return result


if __name__ == "__main__":
    # Prosty test
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    print("🦙 Test OllamaClient\n")

    client = OllamaClient()

    if not client.health_check():
        print("❌ Ollama niedostępny!")
        print("Uruchom: ollama serve")
        exit(1)

    test_text = "Budżet państwa jest abstrakcyjny jak teoria kwantowa"
    print(f"Testuję: '{test_text}'\n")

    result = client.is_statement_funny(test_text)

    print(f"Wynik:")
    print(f"  Śmieszne: {result.is_funny}")
    print(f"  Pewność: {result.confidence:.0%}")
    print(f"  Kategoria: {result.category.value}")
    print(f"  Powód: {result.reason}")
    print(f"\n✓ Test zakończony pomyślnie!")
