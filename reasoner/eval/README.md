# Reasoner Evaluation Harness

This directory contains the evaluation harness for measuring reasoner output quality against golden test cases.

## Overview

The evaluation harness tests the reasoner's ability to produce outputs that meet specific constraints:

- **Tip Count**: 1-2 tips per response
- **Tip Length**: Each tip ≤ 25 words
- **Rationale Length**: ≤ 140 characters
- **Content Safety**: No forbidden terms (profanity, etc.)

## Files

### Golden Test Cases

- **`goldens_tantrum.json`** (15 cases): Tantrum dyad test scenarios
- **`goldens_meal.json`** (15 cases): Meal dyad test scenarios  
- **`goldens_night.json`** (10 cases): Night dyad test scenarios

Each golden case contains:
```json
{
  "features": {"vad_fraction": 0.7, "flux_norm": 0.6},
  "context": {"trigger": "transition", "duration_min": 4},
  "metrics": {"escalation_index": 0.65},
  "expect": {"max_words_per_tip": 25, "tips_max": 2}
}
```

### Evaluation Script

- **`run_eval.py`**: Main evaluation script that tests all golden cases

## Usage

### Prerequisites

1. **Reasoner Service Running**: Ensure the reasoner is running on `http://localhost:5001`
2. **Ollama Available**: Make sure Ollama is running with the required model
3. **Dependencies**: Install required Python packages (`requests`)

### Running Evaluation

```bash
# Run evaluation against default reasoner URL
python reasoner/eval/run_eval.py

# Run evaluation against custom reasoner URL
python reasoner/eval/run_eval.py --reasoner-url http://localhost:5002
```

### Expected Output

The evaluation will:
1. Test each golden case against the reasoner
2. Validate output constraints
3. Generate a detailed Markdown report
4. Exit with code 0 if pass rate ≥ 90%, 1 otherwise

Example output:
```
🚀 Starting Reasoner Evaluation
========================================
🧪 Evaluating tantrum dyad...
  Test 1/15... ✅ PASS (1.23s)
  Test 2/15... ✅ PASS (0.98s)
  ...

🧪 Evaluating meal dyad...
  Test 1/15... ✅ PASS (1.15s)
  ...

🧪 Evaluating night dyad...
  Test 1/10... ✅ PASS (1.08s)
  ...

========================================
📊 EVALUATION REPORT
========================================
# Reasoner Evaluation Report

## Tantrum Dyad
- **Tests**: 15
- **Passed**: 14
- **Pass Rate**: 93.3%
- **Avg Latency**: 1.12s

## Overall Summary
- **Total Tests**: 40
- **Total Passed**: 37
- **Overall Pass Rate**: 92.5%
- **Overall Avg Latency**: 1.08s

🎉 **EVALUATION PASSED** - Pass rate ≥ 90%
```

## Evaluation Criteria

### Pass/Fail Conditions

A test case **PASSES** if all of the following are true:
- ✅ **Tip Count**: 1-2 tips returned
- ✅ **Tip Length**: Each tip ≤ 25 words
- ✅ **Rationale Length**: ≤ 140 characters
- ✅ **Content Safety**: No forbidden terms in tips or rationale

A test case **FAILS** if any of the above conditions are not met.

### Forbidden Terms

The evaluation checks for the following forbidden terms:
- Profanity: fuck, shit, damn, bitch, ass, etc.
- Inappropriate language: cock, dick, pussy, cunt, etc.
- Derogatory terms: whore, slut, bastard, etc.

## Adding Test Cases

To add new test cases:

1. **Edit the appropriate golden file** (`goldens_tantrum.json`, `goldens_meal.json`, or `goldens_night.json`)
2. **Add a new test case** with realistic features, context, and metrics
3. **Run the evaluation** to ensure it works correctly

Example new test case:
```json
{
  "features": {"vad_fraction": 0.5, "flux_norm": 0.4},
  "context": {"trigger": "new_trigger", "duration_min": 3},
  "metrics": {"escalation_index": 0.5},
  "expect": {"max_words_per_tip": 25, "tips_max": 2}
}
```

## Troubleshooting

### Common Issues

1. **Reasoner Not Running**
   ```
   ❌ Error: Connection refused
   ```
   **Solution**: Start the reasoner service on the expected URL

2. **Ollama Not Available**
   ```
   ❌ HTTP 503
   ```
   **Solution**: Ensure Ollama is running with the required model

3. **Timeout Errors**
   ```
   ❌ Error: Request timeout
   ```
   **Solution**: Check reasoner performance or increase timeout in the script

4. **Low Pass Rate**
   ```
   ❌ EVALUATION FAILED - Pass rate < 90%
   ```
   **Solution**: Check reasoner constraints and validation logic

### Debugging

To debug specific test cases:

1. **Check individual responses** in the detailed results table
2. **Review failure analysis** for specific constraint violations
3. **Test manually** using curl or the reasoner API directly
4. **Check reasoner logs** for any errors or warnings

## Performance Expectations

### Latency Targets

- **Cache Hits**: < 100ms
- **Cache Misses**: 500-2000ms (depending on Ollama model)
- **Overall Average**: < 1500ms

### Pass Rate Targets

- **Minimum**: 90% pass rate
- **Target**: 95%+ pass rate
- **Excellent**: 98%+ pass rate

## Integration

The evaluation harness can be integrated into:

- **CI/CD pipelines**: Run on every deployment
- **Development workflow**: Run before merging changes
- **Performance monitoring**: Track pass rates over time
- **Regression testing**: Ensure changes don't break output quality

## Customization

### Modifying Constraints

To modify evaluation constraints, edit the `evaluate_response` method in `run_eval.py`:

```python
def evaluate_response(self, response, golden):
    # Modify constraint checks here
    tip_count_valid = 1 <= len(tips) <= golden['expect']['tips_max']
    tip_words_valid = all(len(tip.split()) <= 25 for tip in tips)
    rationale_valid = len(rationale) <= 140
    # ...
```

### Adding New Metrics

To add new evaluation metrics:

1. **Add metric calculation** in `evaluate_response`
2. **Include in result dictionary**
3. **Update report generation** to display the new metric
4. **Add to pass/fail criteria** if needed 