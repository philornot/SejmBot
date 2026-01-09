"""OpenAI API client for humor evaluation

Uses GPT-4 with optimized prompt for detecting humor in Polish parliamentary statements.
"""

import json
import logging
from typing import Optional, Dict

import requests

from .ai_evaluator import EvaluationResult

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI API humor evaluation"""
    SYSTEM_PROMPT = """Oceń humor w wypowiedzi sejmowej.

ŚMIESZNE:
✓ Żarty, ironia, sarkazm
✓ Absurdy, wpadki  
✓ Reakcje sali (śmiech, oklaski)

NIE ŚMIESZNE:
✗ Zwykłe wypowiedzi
✗ Polemiki polityczne

Odpowiedz JSON (bez preambuły):
{"is_funny": true/false, "confidence": 0.0-1.0, "reason": "krótko"}"""

    def __init__(self, api_key: str, model: str = 'gpt-4o-mini'):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini for cost efficiency)
        """
        self.api_key = api_key
        self.model = model
        self.api_url = 'https://api.openai.com/v1/chat/completions'

        if not self.api_key:
            logger.warning("OpenAI API key not provided")

    def evaluate_humor(self, text: str, context: Optional[Dict] = None) -> Optional[EvaluationResult]:
        """Evaluate if text is funny using OpenAI.

        Args:
            text: Fragment text to evaluate
            context: Optional context (speaker, date, etc.)

        Returns:
            EvaluationResult or None if failed
        """
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")

        # Build user message (keep it short)
        user_message = self._build_message(text, context)

        # Call OpenAI API
        try:
            response = requests.post(
                self.api_url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': self.SYSTEM_PROMPT},
                        {'role': 'user', 'content': user_message}
                    ],
                    'temperature': 0.3,  # Lower for more consistent results
                    'max_tokens': 150,  # Short response = cheaper
                    'response_format': {'type': 'json_object'}  # Enforce JSON response
                },
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            # Parse response
            content = data['choices'][0]['message']['content']
            result_json = json.loads(content)

            return EvaluationResult(
                is_funny=result_json.get('is_funny', False),
                confidence=float(result_json.get('confidence', 0.0)),
                reason=result_json.get('reason', ''),
                api_used='openai'
            )

        except requests.exceptions.RequestException as e:
            snippet = user_message if len(user_message) <= 200 else user_message[:197] + "..."
            logger.error(
                "OpenAI API request failed: %s | model=%s | prompt_snippet=%s",
                e, self.model, snippet,
                exc_info=True
            )
            raise
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(
                "Failed to parse OpenAI response: %s | response=%s",
                e, data.get('choices', [{}])[0].get('message', {}).get('content', '')[:200],
                exc_info=True
            )
            raise

    @staticmethod
    def _build_message(text: str, context: Optional[Dict]) -> str:
        """Build user message with minimal context (shorter = cheaper)."""
        message = f"Wypowiedź:\n{text}"

        if context:
            # Add only essential context
            speaker = context.get('speaker', {})
            if isinstance(speaker, dict) and speaker.get('name'):
                message += f"\nMówca: {speaker['name']}"

        return message
