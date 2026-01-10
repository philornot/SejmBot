# 🤖 AI Integration - Humor Evaluation

SejmBotDetektor now supports AI-powered humor evaluation using OpenAI GPT-4 and Anthropic Claude.

## ✨ Features

Implements 6 Jira tasks (SB-30 through SB-35):

- **SB-30**: OpenAI GPT-4 client for humor detection
- **SB-31**: Anthropic Claude client for humor detection  
- **SB-32**: Optimized prompts for Polish parliamentary humor
- **SB-33**: Automatic fallback between APIs (if one fails, tries the other)
- **SB-34**: Rate limiting and retry logic with exponential backoff
- **SB-35**: Persistent cache to avoid re-evaluating same fragments

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install openai anthropic
```

### 2. Configure API Keys

Copy `.env.example` to `.env` and add your API keys:

```bash
cp SejmBotDetektor/.env.example SejmBotDetektor/.env
# Edit .env and add your keys
```

Get API keys from:
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/

### 3. Run Detector with AI Evaluation

```bash
# Basic usage - evaluate top 50 fragments
python -m SejmBotDetektor.main --ai-evaluate --top-n 50

# With cost optimization - only fragments with score >= 2.0
python -m SejmBotDetektor.main --ai-evaluate --ai-min-score 2.0 --top-n 100

# Prefer specific AI provider
python -m SejmBotDetektor.main --ai-evaluate --ai-provider openai

# Test mode with fixture
python -m SejmBotDetektor.main --ai-evaluate --test-mode
```

## 📊 Output Format

Evaluated fragments include `ai_evaluation` field:

```json
{
  "fragments": [
    {
      "statement_id": 123,
      "text": "Fragment tekstu...",
      "score": 5.5,
      "matched_keywords": [...],
      "ai_evaluation": {
        "is_funny": true,
        "confidence": 0.85,
        "reason": "Zawiera ironię i sarkazm...",
        "api_used": "openai",
        "cached": false,
        "evaluated_at": "2025-12-21T10:30:00"
      }
    }
  ]
}
```

## 💰 Cost Optimization

### Strategies to Reduce API Costs

1. **Filter by score** - Only evaluate high-scoring fragments:
   ```bash
   --ai-min-score 3.0  # Only fragments with score >= 3.0
   ```

2. **Limit quantity** - Evaluate only top N fragments:
   ```bash
   --top-n 50  # Only top 50 fragments
   ```

3. **Use cache** - Cache is automatic and persistent across runs
   - Repeated fragments are never re-evaluated
   - Cache stored in `data/ai_cache/evaluations.json`

4. **Choose cheaper model**:
   ```bash
   # In .env:
   OPENAI_MODEL=gpt-4o-mini  # ~10x cheaper than gpt-4
   ```

### Cost Estimates

Based on current pricing (Dec 2024):

- **gpt-4o-mini**: ~$0.0002 per fragment (500 tokens)
- **gpt-4o**: ~$0.002 per fragment
- **claude-sonnet-4**: ~$0.003 per fragment

Example: 100 fragments with gpt-4o-mini ≈ $0.02

## 🔄 Fallback System (SB-33)

If primary API fails, automatically tries secondary:

```
[Try OpenAI] → [Fails] → [Try Claude] → [Success]
```

Configure primary API in `.env`:
```bash
PRIMARY_AI_API=bielik
```

## 📈 Rate Limiting (SB-34)

Built-in rate limiting to stay within API limits:

- **OpenAI**: 50 calls/minute (configurable)
- **Claude**: 40 calls/minute (configurable)

Auto-waits when limit reached, then resumes.

## 💾 Cache System (SB-35)

### How Cache Works

1. **Text hashing**: Each fragment gets SHA-256 hash
2. **Persistent storage**: Cache saved to `data/ai_cache/evaluations.json`
3. **Auto-save**: Cache saved every 10 evaluations
4. **Cross-run**: Cache persists between runs

### Cache Management

```bash
# View cache stats
python -c "from SejmBotDetektor.ai_evaluator import AIEvaluator; e = AIEvaluator(); print(e.get_stats())"

# Clear cache
python -c "from SejmBotDetektor.ai_evaluator import AIEvaluator; e = AIEvaluator(); e.clear_cache()"
```

## 🧪 Testing

Test AI integration without processing real data:

```bash
# Test with fixture
python -m SejmBotDetektor.main --ai-evaluate --test-mode

# Test specific API
python -m SejmBotDetektor.main --ai-evaluate --ai-provider openai --test-mode
python -m SejmBotDetektor.main --ai-evaluate --ai-provider claude --test-mode
```

## 🐛 Troubleshooting

### "OpenAI API key not configured"
- Check `.env` file exists in `SejmBotDetektor/` directory
- Verify `OPENAI_API_KEY` is set correctly
- Don't commit `.env` to git (it's in `.gitignore`)

### "Rate limit reached"
- Detector automatically waits and retries
- Reduce `--top-n` to evaluate fewer fragments
- Increase wait time by setting lower rate limits in code

### "Both APIs failed"
- Check API keys are valid
- Verify network connection
- Check API status pages:
  - OpenAI: https://status.openai.com/
  - Anthropic: https://status.anthropic.com/

### High costs
- Use `--ai-min-score` to filter fragments
- Reduce `--top-n` value
- Switch to cheaper model (gpt-4o-mini)
- Check cache is being used (should see "cached" in output)

## 📝 Advanced Usage

### Programmatic API

```python
from SejmBotDetektor.ai_evaluator import AIEvaluator

# Initialize
evaluator = AIEvaluator()

# Evaluate single fragment
result = evaluator.evaluate_fragment(
    text="Jakaś wypowiedź z sejmu...",
    context={'speaker': {'name': 'Jan Kowalski', 'club': 'KO'}}
)

print(f"Śmieszne: {result.is_funny}")
print(f"Pewność: {result.confidence}")
print(f"Powód: {result.reason}")

# Evaluate batch
fragments = [
    {'text': 'Fragment 1...', 'score': 5.0},
    {'text': 'Fragment 2...', 'score': 3.5},
]
evaluated = evaluator.evaluate_fragments_batch(fragments)

# Check stats
stats = evaluator.get_stats()
print(f"Cache size: {stats['cache_size']}")
print(f"API calls: OpenAI={stats['openai_calls']}, Claude={stats['claude_calls']}")
```

## 🔐 Security

- **Never commit `.env` file** to git
- API keys have full access to your account - keep them secret
- Set spending limits in OpenAI/Anthropic dashboards
- Rotate keys periodically

## 📚 Prompt Engineering (SB-32)

Prompts are optimized for Polish parliamentary humor detection:

**Key criteria:**
- Intentional jokes, irony, sarcasm
- Unintentional comedy (absurdity, linguistic errors)
- Funny situations, unexpected comparisons
- Audience reactions (laughter, applause)

**Not considered funny:**
- Regular policy discussions
- Political arguments without humor
- Standard parliamentary procedures

See `openai_client.py` and `claude_client.py` for full prompts.

## 🤝 Contributing

To improve AI evaluation:

1. **Adjust prompts** in `openai_client.py` / `claude_client.py`
2. **Add evaluation metrics** in `ai_evaluator.py`
3. **Tune confidence thresholds** based on validation data
4. **Expand cache** with manual annotations

## 📊 Next Steps

After AI evaluation, top funny fragments can be:

1. **Manually reviewed** for final selection
2. **Linked to video** timestamps from proceedings
3. **Sent to mobile app** as push notifications
4. **Stored in database** for SejmBot app

---

**Status**: ✅ All 6 tasks (SB-30 through SB-35) implemented and tested

**Questions?** Check main README or create an issue.