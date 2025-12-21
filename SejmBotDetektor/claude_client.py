"""Claude API client for humor evaluation (SB-31).

Uses Claude Sonnet with optimized prompt for detecting humor in Polish parliamentary statements.
"""

import json
import logging
from typing import Optional, Dict

import requests

from .ai_evaluator import EvaluationResult

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for Anthropic Claude API humor evaluation (SB-31)."""

    # Optimized prompt for humor detection (SB-32)
    SYSTEM_PROMPT = """Jesteś ekspertem od analizy humoru w polskich wystąpieniach sejmowych.

Oceniasz, czy fragmenty wypowiedzi są śmieszne lub mają potencjał humorystyczny.

**Kryteria śmieszności:**
✓ Celowe żarty, ironia, sarkazm
✓ Niezamierzona komiczność (absurdy, wpadki)
✓ Zabawne sytuacje, nieoczekiwane porównania  
✓ Reakcje sali (śmiech, oklaski, poruszenie)

**NIE jest śmieszne:**
✗ Zwykłe wypowiedzi merytoryczne
✗ Polemiki polityczne bez humoru
✗ Standardowe procedury

Odpowiadaj TYLKO w formacie JSON (bez preambuły):
{
  "is_funny": true/false,
  "confidence": 0.0-1.0,
  "reason": "zwięzłe wyjaśnienie"
}"""

    def __init__(self, api_key: str, model: str = 'claude-sonnet-4-20250514'):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.api_key = api_key
        self.model = model
        self.api_url = 'https://api.anthropic.com/v1/messages'

        if not self.api_key:
            logger.warning("Claude API key not provided")

    def evaluate_humor(self, text: str, context: Optional[Dict] = None) -> Optional[EvaluationResult]:
        """Evaluate if text is funny using Claude.

        Args:
            text: Fragment text to evaluate
            context: Optional context (speaker, date, etc.)

        Returns:
            EvaluationResult or None if failed
        """
        if not self.api_key:
            raise ValueError("Claude API key not configured")

        # Build user message with context
        user_message = self._build_message(text, context)

        # Call Claude API
        try:
            response = requests.post(
                self.api_url,
                headers={
                    'x-api-key': self.api_key,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json'
                },
                json={
                    'model': self.model,
                    'max_tokens': 200,
                    'temperature': 0.3,
                    'system': self.SYSTEM_PROMPT,
                    'messages': [
                        {'role': 'user', 'content': user_message}
                    ]
                },
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            # Parse Claude response
            content = data['content'][0]['text']

            # Claude might add preamble - extract JSON
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if 0 <= json_start < json_end:
                content = content[json_start:json_end]

            result_json = json.loads(content)

            return EvaluationResult(
                is_funny=result_json.get('is_funny', False),
                confidence=float(result_json.get('confidence', 0.0)),
                reason=result_json.get('reason', ''),
                api_used='claude'
            )

        except requests.exceptions.RequestException as e:
            logger.error(
                "Błąd żądania Claude API (model=%s, tekst_skrot=%r): %s",
                getattr(self, "model", None),
                (text[:120] + "…") if len(text) > 120 else text,
                e,
            )
            raise
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(
                "Nie udało się zinterpretować odpowiedzi Claude (model=%s, tekst_skrot=%r, surowa_odpowiedz_skrot=%r): %s",
                getattr(self, "model", None),
                (text[:120] + "…") if len(text) > 120 else text,
                (str(locals().get("data"))[:200] if locals().get("data") is not None else None),
                e,
            )
            raise

    @staticmethod
    def _build_message(text: str, context: Optional[Dict]) -> str:
        """Build user message with optional context."""
        message = f"Oceń humor tej wypowiedzi sejmowej:\n\n{text}"

        if context:
            # Add speaker info
            speaker = context.get('speaker', {})
            if isinstance(speaker, dict) and speaker.get('name'):
                message += f"\n\nMówca: {speaker['name']}"
                if speaker.get('club'):
                    message += f" ({speaker['club']})"

            # Add keywords hint
            keywords = context.get('matched_keywords', [])
            if keywords:
                kw_list = ', '.join(k.get('keyword', '') for k in keywords if k.get('keyword'))
                message += f"\n\nSłowa-klucze: {kw_list}"

        return message
