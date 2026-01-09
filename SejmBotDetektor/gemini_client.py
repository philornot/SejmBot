"""Google Gemini client for humor evaluation - FREE TIER
Uses Gemini 1.5 Flash (free, fast, good for Polish)
API key: https://aistudio.google.com/app/apikey
"""

import json
import logging
from typing import Optional, Dict

import requests

from .ai_evaluator import EvaluationResult

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for Google Gemini API (FREE tier)"""

    # Krótszy, lepszy prompt (oszczędza tokeny)
    SYSTEM_PROMPT = """Oceń humor w wypowiedzi sejmowej.

ŚMIESZNE:
✓ Żarty, ironia, sarkazm
✓ Absurdy, wpadki
✓ Reakcje sali (śmiech, oklaski)

NIE ŚMIESZNE:
✗ Zwykłe wypowiedzi
✗ Polemiki polityczne

Odpowiedz JSON (bez ``` i preambuły):
{"is_funny": true/false, "confidence": 0.0-1.0, "reason": "krótko"}"""

    def __init__(self, api_key: str, model: str = 'gemini-2.5-flash-lite'):
        """Initialize Gemini client.

        Args:
            api_key: Google AI Studio API key
            model: Model name (gemini-2.5-flash-lite is FREE and fast)
        """
        self.api_key = api_key
        self.model = model
        self.api_url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'

        if not self.api_key:
            logger.warning("Gemini API key not provided")

    def evaluate_humor(self, text: str, context: Optional[Dict] = None) -> Optional[EvaluationResult]:
        """Evaluate if text is funny using Gemini.

        Args:
            text: Fragment text to evaluate
            context: Optional context (speaker, date, etc.)

        Returns:
            EvaluationResult or None if failed
        """
        if not self.api_key:
            raise ValueError("Gemini API key not configured")

        # Build prompt (krótszy = taniej)
        user_message = f"{self.SYSTEM_PROMPT}\n\nWypowiedź:\n{text}"

        # Add minimal context
        if context:
            speaker = context.get('speaker', {})
            if isinstance(speaker, dict) and speaker.get('name'):
                user_message += f"\nMówca: {speaker['name']}"

        try:
            response = requests.post(
                self.api_url,
                headers={'Content-Type': 'application/json'},
                params={'key': self.api_key},
                json={
                    'contents': [{
                        'parts': [{'text': user_message}]
                    }],
                    'generationConfig': {
                        'temperature': 0.3,  # Bardziej deterministyczny
                        'maxOutputTokens': 150,  # Krótka odpowiedź
                        'topP': 0.8,
                        'topK': 10
                    }
                },
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            # Parse Gemini response
            if not data.get('candidates'):
                logger.warning("No candidates in Gemini response")
                return None

            content = data['candidates'][0]['content']['parts'][0]['text']

            # Extract JSON (Gemini sometimes adds text around it)
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if 0 <= json_start < json_end:
                content = content[json_start:json_end]

            result_json = json.loads(content)

            return EvaluationResult(
                is_funny=result_json.get('is_funny', False),
                confidence=float(result_json.get('confidence', 0.0)),
                reason=result_json.get('reason', ''),
                api_used='gemini'
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Gemini API request failed: {e}")
            raise
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise