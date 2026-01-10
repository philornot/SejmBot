"""Demo script for AI-powered humor evaluation.

Shows how to use the AI evaluator to detect funny fragments.

Requirements:
    pip install openai anthropic

Setup:
    1. Copy SejmBotDetektor/.env.example to SejmBotDetektor/.env
    2. Add your API keys to .env
    3. Run: python SejmBotDetektor/examples/ai_evaluation_demo.py
"""

import sys
from pathlib import Path

from SejmBotDetektor.ai_evaluator import AIEvaluator

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def demo_single_evaluation():
    """Demo: Evaluate single fragment."""
    print("=== DEMO 1: Single Fragment Evaluation ===\n")

    evaluator = AIEvaluator()

    # Test fragments
    test_cases = [
        {
            'text': 'Ten żart był naprawdę śmieszny i pełen humoru. (Oklaski)',
            'context': {'speaker': {'name': 'Jan Kowalski', 'club': 'KO'}}
        },
        {
            'text': 'Dyskusja o kryzysie energetycznym i inflacji w kraju.',
            'context': {'speaker': {'name': 'Anna Nowak', 'club': 'PiS'}}
        },
        {
            'text': 'Panie Marszałku! To jest skandal i hańba! (Głos z sali: "Brawo!")',
            'context': {}
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"Fragment {i}:")
        print(f"  Text: {test['text'][:60]}...")

        result = evaluator.evaluate_fragment(test['text'], test['context'])

        print(f"  ✨ Funny: {result.is_funny}")
        print(f"  📊 Confidence: {result.confidence:.2f}")
        print(f"  💭 Reason: {result.reason}")
        print(f"  🤖 API: {result.api_used}")
        print(f"  💾 Cached: {result.cached}")
        print()


def demo_batch_evaluation():
    """Demo: Evaluate multiple fragments efficiently."""
    print("\n=== DEMO 2: Batch Evaluation ===\n")

    evaluator = AIEvaluator()

    # Simulate fragments from detector
    fragments = [
        {
            'text': 'To jest absurd! Kompletny absurd! (Śmiech na sali)',
            'score': 5.5,
            'matched_keywords': [
                {'keyword': 'absurd', 'count': 2, 'weight': 2.0}
            ]
        },
        {
            'text': 'Panie Pośle, czy Pan żartuje? (Wesołość na sali)',
            'score': 4.0,
            'matched_keywords': [
                {'keyword': 'żartuje', 'count': 1, 'weight': 2.0}
            ]
        },
        {
            'text': 'Przedstawiam projekt ustawy o finansach publicznych.',
            'score': 1.0,
            'matched_keywords': []
        }
    ]

    print(f"Evaluating {len(fragments)} fragments...\n")

    evaluated = evaluator.evaluate_fragments_batch(fragments)

    # Show results
    funny_fragments = [f for f in evaluated if f.get('ai_evaluation', {}).get('is_funny')]

    print(f"📊 Results:")
    print(f"  Total evaluated: {len(evaluated)}")
    print(f"  Funny fragments: {len(funny_fragments)}")
    print(f"  Cache hits: {sum(1 for f in evaluated if f.get('ai_evaluation', {}).get('cached'))}")

    print(f"\n✨ Funny fragments:")
    for f in funny_fragments:
        eval_data = f['ai_evaluation']
        print(f"  - {f['text'][:50]}...")
        print(f"    Confidence: {eval_data['confidence']:.2f}, Reason: {eval_data['reason'][:60]}...")


def demo_cache_and_stats():
    """Demo: Cache functionality and statistics."""
    print("\n=== DEMO 3: Cache & Statistics ===\n")

    evaluator = AIEvaluator()

    # Evaluate same fragment twice
    text = "Czy ktoś ma chusteczkę? (Śmiech)"

    print("First evaluation (will call API):")
    result1 = evaluator.evaluate_fragment(text)
    print(f"  Cached: {result1.cached}, API: {result1.api_used}")

    print("\nSecond evaluation (will use cache):")
    result2 = evaluator.evaluate_fragment(text)
    print(f"  Cached: {result2.cached}, API: {result2.api_used}")

    # Show stats
    stats = evaluator.get_stats()
    print(f"\n📈 Evaluator Statistics:")
    print(f"  Cache size: {stats['cache_size']} entries")
    print(f"  Cache file: {stats['cache_file']}")
    print(f"  Primary API: {stats['primary_api']}")
    print(f"  OpenAI calls: {stats['openai_calls']}")
    print(f"  Claude calls: {stats['claude_calls']}")


def demo_fallback():
    """Demo: Fallback between APIs."""
    print("\n=== DEMO 4: API Fallback ===\n")

    print("This demo shows how evaluator automatically falls back")
    print("from primary API to secondary if primary fails.")
    print()
    print("Try running with only one API key configured to see fallback in action!")
    print()

    # Create evaluator with explicit primary
    evaluator = AIEvaluator(config={'primary_api': 'ollama'})

    text = "Ha, ha, ha! To było dobre! (Oklaski)"

    print(f"Primary API: {evaluator.config['primary_api']}")
    print(f"Evaluating: {text}")

    result = evaluator.evaluate_fragment(text)

    print(f"\n✓ Success!")
    print(f"  API used: {result.api_used}")
    print(f"  Result: {result.is_funny} (confidence: {result.confidence:.2f})")


def main():
    """Run all demos."""
    print("🤖 SejmBotDetektor - AI Evaluation Demo\n")
    print("This demo shows all features of the AI integration:")
    print("  - Single fragment evaluation")
    print("  - Batch processing")
    print("  - Cache system")
    print("  - API fallback")
    print()

    try:
        demo_single_evaluation()
        demo_batch_evaluation()
        demo_cache_and_stats()
        demo_fallback()

        print("\n✅ Demo completed successfully!")
        print("\nNext steps:")
        print("  1. Run full detector: python -m SejmBotDetektor.main --ai-evaluate")
        print("  2. Read docs: SejmBotDetektor/AI_INTEGRATION.md")
        print("  3. Adjust prompts in openai_client.py / claude_client.py")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check .env file exists with API keys")
        print("  2. Install dependencies: pip install openai anthropic")
        print("  3. Check API key validity")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
