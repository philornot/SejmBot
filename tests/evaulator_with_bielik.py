# test_evaluator_with_bielik.py
import logging
from SejmBotDetektor.ai_evaluator import AIEvaluator

logging.basicConfig(level=logging.INFO)

evaluator = AIEvaluator()

# Test
fragments = [
    {'text': 'Budżet jest abstrakcyjny jak teoria kwantowa'},
    {'text': 'Przystępujemy do głosowania nad ustawą'}
]

results = evaluator.evaluate_fragments_batch(fragments)

for r in results:
    eval_data = r['ai_evaluation']
    print(f"Funny: {eval_data['is_funny']}, API: {eval_data['api_used']}, Conf: {eval_data['confidence']:.0%}")