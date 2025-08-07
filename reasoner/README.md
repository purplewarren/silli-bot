# Silli Reasoner

AI-powered reasoning engine for Silli's dyad insights. Integrates with local Ollama runtime to generate personalized tips and rationale based on child development data.

## Features

- **Local AI Processing**: Uses Ollama for on-device AI reasoning
- **Dyad-Specific Analysis**: Tailored insights for night, tantrum, and meal scenarios
- **Privacy-First**: PII redaction and no raw media transmission
- **Structured Output**: Consistent tips and rationale format
- **Metric Overrides**: Optional AI-suggested metric adjustments

## Prerequisites

### 1. Install Ollama

```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download
```

### 2. Pull Required Model

```bash
# Pull the recommended model
ollama pull gpt-oss-20b

# Or use a smaller model for faster inference
ollama pull llama3.2:3b
```

### 3. Start Ollama

```bash
# Start Ollama server
ollama serve
```

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt
```

## Usage

### Start the Reasoner

```bash
# Start the Flask server
python app.py

# Or with custom port
PORT=5002 python app.py
```

The reasoner will start on `http://localhost:5001` by default.

### API Endpoints

#### Health Check
```bash
curl http://localhost:5001/health
```

#### List Models
```bash
curl http://localhost:5001/models
```

#### Reasoning Request
```bash
curl -X POST http://localhost:5001/v1/reason \
  -H "Content-Type: application/json" \
  -d '{
    "dyad": "tantrum",
    "features": {
      "vad_fraction": 0.45,
      "flux_norm": 0.32
    },
    "context": {
      "trigger": "transition",
      "duration_min": 4
    },
    "metrics": {
      "escalation_index": 0.65
    },
    "history": []
  }'
```

## Request Schema

### ReasoningRequest
```typescript
{
  dyad: "night" | "tantrum" | "meal",
  features: {
    // Audio/video features (no raw data)
    vad_fraction?: number,
    flux_norm?: number,
    level_dbfs?: number,
    // Image features
    dietary_diversity?: number,
    clutter_score?: number,
    plate_coverage?: number
  },
  context: {
    // User-provided context (PII will be redacted)
    trigger?: string,
    duration_min?: number,
    meal_type?: string,
    eaten_pct?: number,
    stress_level?: number
  },
  metrics: {
    escalation_index?: number,  // 0.0-1.0
    meal_mood?: number          // 0-100
  },
  history: Array<{
    timestamp: string,
    escalation_index?: number,
    meal_mood?: number,
    trigger?: string
  }>
}
```

### ReasoningResponse
```typescript
{
  tips: string[],           // Up to 2 actionable tips
  rationale: string,        // Explanation of reasoning
  metric_overrides?: {      // Optional metric adjustments
    escalation_index?: number,
    meal_mood?: number
  },
  response_time: number,    // Response time in seconds
  dyad: string
}
```

## Configuration

### Environment Variables

- `OLLAMA_HOST`: Ollama server URL (default: `http://localhost:11434`)
- `PORT`: Flask server port (default: `5001`)

### Model Configuration

The reasoner uses `gpt-oss-20b` by default. To use a different model:

1. Update the model name in `app.py`:
```python
ollama_response = ollama_client.post_chat(
    messages=messages,
    temperature=0.2,
    model="llama3.2:3b"  # Change model here
)
```

2. Pull the desired model:
```bash
ollama pull llama3.2:3b
```

## Testing

### Run Test Suite

```bash
# Start the reasoner first
python app.py

# In another terminal, run tests
python test_reasoner.py
```

### Manual Testing

```bash
# Test health check
curl http://localhost:5001/health

# Test tantrum reasoning
curl -X POST http://localhost:5001/v1/reason \
  -H "Content-Type: application/json" \
  -d @test_tantrum.json

# Test meal reasoning
curl -X POST http://localhost:5001/v1/reason \
  -H "Content-Type: application/json" \
  -d @test_meal.json
```

## Security & Privacy

### PII Redaction
The reasoner automatically redacts PII fields:
- `name`, `email`, `phone`, `address`
- `child_name`, `family_name`
- `notes`, `description`, `comments`, `details`

### Media Safety
- Raw media data is never sent to Ollama
- Only computed features are transmitted
- No audio/video/image data leaves the device

### Metric Validation
- All metric overrides are clamped to valid ranges
- `escalation_index`: 0.0-1.0
- `meal_mood`: 0-100

## Performance

### Expected Response Times
- **gpt-oss-20b**: 3-6 seconds
- **llama3.2:3b**: 1-3 seconds
- **llama3.2:1b**: 0.5-2 seconds

### Optimization Tips
1. Use smaller models for faster inference
2. Reduce temperature for more consistent outputs
3. Limit history to recent sessions only
4. Use SSD storage for model loading

## Troubleshooting

### Common Issues

#### Ollama Not Running
```
Error: Ollama runtime not available
```
**Solution**: Start Ollama with `ollama serve`

#### Model Not Found
```
Error: Model 'gpt-oss-20b' not found
```
**Solution**: Pull the model with `ollama pull gpt-oss-20b`

#### Slow Response Times
**Solutions**:
- Use a smaller model
- Check system resources
- Ensure SSD storage
- Reduce temperature setting

#### Memory Issues
**Solutions**:
- Use smaller models
- Close other applications
- Increase system memory
- Use model quantization

### Debug Mode

Enable debug logging:
```bash
FLASK_DEBUG=1 python app.py
```

### Logs

Check Ollama logs:
```bash
ollama logs
```

## Integration

### With Silli Bot
The reasoner can be integrated with the Silli bot to provide AI-powered insights:

```python
# In bot code
import requests

def get_ai_insights(dyad, features, context, metrics, history):
    response = requests.post(
        'http://localhost:5001/v1/reason',
        json={
            'dyad': dyad,
            'features': features,
            'context': context,
            'metrics': metrics,
            'history': history
        }
    )
    return response.json()
```

### With PWA
The PWA can call the reasoner for enhanced insights:

```javascript
// In PWA code
async function getReasoning(dyad, features, context, metrics, history) {
  const response = await fetch('http://localhost:5001/v1/reason', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dyad, features, context, metrics, history })
  });
  return response.json();
}
```

## Development

### Adding New Dyads
1. Update the dyad validation in `app.py`
2. Add dyad-specific prompts to the system message
3. Update the test suite with new dyad examples

### Customizing Prompts
Modify the system prompt in `app.py` to change the AI's behavior:

```python
system_prompt = """You are Silli's reasoning engine. 
Customize this prompt for your specific needs.
"""
```

### Extending Response Format
Update the `ReasoningResponse` dataclass and parsing logic to include new fields.

## License

This project is part of Silli AI and follows the same licensing terms. 