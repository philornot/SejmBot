"""
AI Evaluator for humor detection
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Literal

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of AI humor evaluation."""
    is_funny: bool
    confidence: float  # 0.0 - 1.0
    reason: str
    api_used: Literal['openai', 'claude', 'gemini', 'none']
    cached: bool = False
    evaluated_at: str = None

    def __post_init__(self):
        if self.evaluated_at is None:
            self.evaluated_at = datetime.now().isoformat()


class AIEvaluator:
    """Main orchestrator for AI-powered humor evaluation - OPTIMIZED"""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize AI evaluator with optional config."""
        self.config = config or self._load_config()

        # Initialize API clients lazily
        self._openai_client = None
        self._claude_client = None
        self._gemini_client = None

        # Cache setup
        cache_dir = Path(self.config.get('cache_dir', 'data/ai_cache'))
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = cache_dir / 'evaluations.json'
        self.cache = self._load_cache()

        # Rate limiting 
        self.rate_limits = {
            'openai': {'calls': 0, 'reset_time': time.time(), 'max_per_minute': 50},
            'claude': {'calls': 0, 'reset_time': time.time(), 'max_per_minute': 40},
            'gemini': {'calls': 0, 'reset_time': time.time(), 'max_per_minute': 60}  # Gemini is generous
        }

        logger.info("AI Evaluator initialized (with Gemini support)")

    @staticmethod
    def _load_config() -> Dict:
        """Load configuration from environment or defaults."""
        import os
        return {
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY'),
            'gemini_api_key': os.getenv('GEMINI_API_KEY'),
            'openai_model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            'claude_model': os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514'),
            'gemini_model': os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite'),
            'primary_api': os.getenv('PRIMARY_AI_API', 'gemini'),  # FREE first
            'cache_dir': os.getenv('AI_CACHE_DIR', 'data/ai_cache'),
            'max_retries': int(os.getenv('AI_MAX_RETRIES', '2')),
        }

    def _load_cache(self) -> Dict:
        """Load evaluation cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    logger.info(f"Loaded {len(cache)} cached evaluations")
                    return cache
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        return {}

    def _save_cache(self):
        """Save evaluation cache to disk."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    @staticmethod
    def _get_cache_key(text: str) -> str:
        """Generate cache key from text hash."""
        # Normalize text for better deduplication
        normalized = text.lower().strip()
        normalized = ' '.join(normalized.split())  # Normalize whitespace
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def _check_cache(self, text: str) -> Optional[EvaluationResult]:
        """Check if evaluation exists in cache ."""
        key = self._get_cache_key(text)
        if key in self.cache:
            cached_data = self.cache[key]
            result = EvaluationResult(**cached_data)
            result.cached = True
            logger.debug(f"Cache hit for fragment")
            return result
        return None

    def _store_in_cache(self, text: str, result: EvaluationResult):
        """Store evaluation result in cache."""
        key = self._get_cache_key(text)
        self.cache[key] = asdict(result)

        # Save cache periodically (every 10 evaluations)
        if len(self.cache) % 10 == 0:
            self._save_cache()

    def _check_rate_limit(self, api: str) -> bool:
        """Check if we can make API call within rate limits ."""
        limit_info = self.rate_limits[api]
        current_time = time.time()

        # Reset counter if minute passed
        if current_time - limit_info['reset_time'] > 60:
            limit_info['calls'] = 0
            limit_info['reset_time'] = current_time

        # Check if under limit
        if limit_info['calls'] < limit_info['max_per_minute']:
            limit_info['calls'] += 1
            return True

        logger.warning(f"Rate limit reached for {api}, waiting...")
        return False

    def _wait_for_rate_limit(self, api: str):
        """Wait until rate limit resets."""
        limit_info = self.rate_limits[api]
        wait_time = 60 - (time.time() - limit_info['reset_time'])
        if wait_time > 0:
            logger.info(f"Waiting {wait_time:.1f}s for {api} rate limit reset")
            time.sleep(wait_time)
            limit_info['calls'] = 0
            limit_info['reset_time'] = time.time()

    @property
    def openai_client(self):
        """Lazy initialization of OpenAI client."""
        if self._openai_client is None:
            from .openai_client import OpenAIClient
            self._openai_client = OpenAIClient(
                api_key=self.config['openai_api_key'],
                model=self.config['openai_model']
            )
        return self._openai_client

    @property
    def claude_client(self):
        """Lazy initialization of Claude client."""
        if self._claude_client is None:
            from .claude_client import ClaudeClient
            self._claude_client = ClaudeClient(
                api_key=self.config['anthropic_api_key'],
                model=self.config['claude_model']
            )
        return self._claude_client

    @property
    def gemini_client(self):
        """Lazy initialization of Gemini client (FREE)."""
        if self._gemini_client is None:
            from .gemini_client import GeminiClient
            self._gemini_client = GeminiClient(
                api_key=self.config['gemini_api_key'],
                model=self.config['gemini_model']
            )
        return self._gemini_client

    def evaluate_fragment(self, text: str, context: Optional[Dict] = None) -> EvaluationResult:
        """Evaluate if a fragment is funny using AI.

        Implements smart fallback :
        1. Try FREE option (Gemini) first
        2. Fall back to paid options if needed

        Args:
            text: Fragment text to evaluate
            context: Optional context (speaker, date, etc.)

        Returns:
            EvaluationResult with is_funny, confidence, reason
        """
        # Check cache first 
        cached = self._check_cache(text)
        if cached:
            return cached

        # Determine API order - FREE first
        primary = self.config['primary_api']

        # Smart ordering: free -> paid
        if primary == 'gemini':
            apis = ['gemini', 'openai', 'claude']
        elif primary == 'openai':
            apis = ['openai', 'gemini', 'claude']
        else:
            apis = ['claude', 'gemini', 'openai']

        last_error = None

        # Try each API with fallback 
        for api_name in apis:
            try:
                # Check rate limit 
                if not self._check_rate_limit(api_name):
                    self._wait_for_rate_limit(api_name)

                # Get appropriate client
                if api_name == 'openai':
                    client = self.openai_client
                elif api_name == 'claude':
                    client = self.claude_client
                else:  # gemini
                    client = self.gemini_client

                # Evaluate with retry logic 
                result = self._evaluate_with_retry(client, text, context, api_name)

                if result:
                    # Store in cache 
                    self._store_in_cache(text, result)
                    return result

            except Exception as e:
                logger.warning(f"{api_name} evaluation failed: {e}")
                last_error = e
                continue

        # All APIs failed - return conservative result
        logger.error(f"All APIs failed. Last error: {last_error}")
        return EvaluationResult(
            is_funny=False,
            confidence=0.0,
            reason=f"Evaluation failed: {last_error}",
            api_used='none',
            cached=False
        )

    def _evaluate_with_retry(self, client, text: str, context: Optional[Dict],
                             api_name: str) -> Optional[EvaluationResult]:
        """Evaluate with retry logic ."""
        max_retries = self.config['max_retries']

        for attempt in range(max_retries):
            try:
                # Call client's evaluate method
                result = client.evaluate_humor(text, context)

                if result:
                    result.api_used = api_name
                    result.cached = False
                    logger.info(f"✓ {api_name} evaluation: funny={result.is_funny} conf={result.confidence:.2f}")
                    return result

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.warning(f"{api_name} attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

        return None

    def evaluate_fragments_batch(self, fragments: List[Dict]) -> List[Dict]:
        """Evaluate multiple fragments efficiently.

        Args:
            fragments: List of fragment dicts with 'text' field

        Returns:
            List of fragments enriched with evaluation results
        """
        logger.info(f"Evaluating {len(fragments)} fragments...")

        results = []
        cached_count = 0
        funny_count = 0

        for i, fragment in enumerate(fragments, 1):
            text = fragment.get('text', '')

            if not text or len(text) < 20:
                continue

            # Show progress every 10 fragments
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(fragments)} ({funny_count} funny, {cached_count} cached)")

            # Evaluate
            evaluation = self.evaluate_fragment(text, context=fragment)

            # Track stats
            if evaluation.cached:
                cached_count += 1
            if evaluation.is_funny:
                funny_count += 1

            # Enrich fragment with evaluation
            enriched = fragment.copy()
            enriched['ai_evaluation'] = asdict(evaluation)
            results.append(enriched)

            # Small delay between API calls (only if not cached)
            if not evaluation.cached:
                time.sleep(0.5)

        # Save cache after batch
        self._save_cache()

        logger.info(f"✓ Evaluated {len(results)} fragments: {funny_count} funny, {cached_count} from cache")
        return results

    def get_stats(self) -> Dict:
        """Get evaluator statistics."""
        return {
            'cache_size': len(self.cache),
            'cache_file': str(self.cache_file),
            'openai_calls': self.rate_limits['openai']['calls'],
            'claude_calls': self.rate_limits['claude']['calls'],
            'gemini_calls': self.rate_limits['gemini']['calls'],
            'primary_api': self.config['primary_api'],
        }

    def clear_cache(self):
        """Clear evaluation cache."""
        self.cache.clear()
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("Cache cleared")


if __name__ == '__main__':
    # Quick test
    logging.basicConfig(level=logging.INFO)

    evaluator = AIEvaluator()

    test_fragments = [
        "Ten żart był naprawdę śmieszny i pełen humoru.",
        "Dyskusja o kryzysie energetycznym i inflacji w kraju.",
    ]

    for text in test_fragments:
        result = evaluator.evaluate_fragment(text)
        print(f"\nText: {text[:60]}...")
        print(f"Funny: {result.is_funny} (confidence: {result.confidence:.2f})")
        print(f"Reason: {result.reason}")
        print(f"API: {result.api_used}, Cached: {result.cached}")
