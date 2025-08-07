#!/usr/bin/env python3
"""
Silli Reasoner - AI-powered reasoning engine for dyad insights
Integrates with local Ollama runtime for generating tips and rationale
"""

import json
import os
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from flask import Flask, request, jsonify
from ollama_client import OllamaClient, create_system_message, create_user_message
from prompts import get_prompt
from validators import validate_reasoning
from cache import ReasonerCache

app = Flask(__name__)

# Initialize Ollama client
ollama_client = OllamaClient()

# Initialize cache
cache = ReasonerCache()

@dataclass
class ReasoningRequest:
    dyad: str  # "night", "tantrum", "meal"
    features: Dict[str, Any]  # Audio/video features
    context: Dict[str, Any]  # User-provided context
    metrics: Dict[str, Any]  # Computed metrics
    history: List[Dict[str, Any]]  # Recent sessions

@dataclass
class ReasoningResponse:
    tips: List[str]  # Up to 2 actionable tips
    rationale: str  # Explanation of reasoning
    metric_overrides: Optional[Dict[str, float]] = None  # Optional metric adjustments

def redact_pii(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove PII fields from data"""
    pii_fields = {
        'name', 'email', 'phone', 'address', 'child_name', 'family_name',
        'notes', 'description', 'comments', 'details'
    }
    
    def _redact_recursive(obj):
        if isinstance(obj, dict):
            return {k: '[REDACTED]' if k.lower() in pii_fields else _redact_recursive(v) 
                   for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_redact_recursive(item) for item in obj]
        else:
            return obj
    
    return _redact_recursive(data)

def prepare_user_message(request_data: ReasoningRequest) -> str:
    """Prepare user message for Ollama from reasoning request"""
    
    # Get dyad-specific prompt template
    prompt = get_prompt(request_data.dyad)
    
    # Redact PII and prepare clean data
    clean_context = redact_pii(request_data.context)
    clean_history = redact_pii(request_data.history)
    
    # Remove raw media data
    clean_features = {}
    if request_data.features:
        for key, value in request_data.features.items():
            if not key.startswith('raw_') and not key.endswith('_data'):
                clean_features[key] = value
    
    # Prepare user message with prompt template
    user_data = {
        "dyad": request_data.dyad,
        "constraints": prompt["constraints"],
        "few_shot": prompt["few_shot"],
        "features": clean_features,
        "context": clean_context,
        "metrics": request_data.metrics,
        "recent": clean_history[:3] if clean_history else []  # Last 3 sessions
    }
    
    return json.dumps(user_data, indent=2)

def parse_ollama_response(response: str) -> ReasoningResponse:
    """Parse Ollama response into structured reasoning response with validation"""
    
    try:
        # Try to parse as JSON first
        response_clean = response.strip()
        
        # Remove any markdown code blocks
        if response_clean.startswith('```json'):
            response_clean = response_clean[7:]
        if response_clean.startswith('```'):
            response_clean = response_clean[3:]
        if response_clean.endswith('```'):
            response_clean = response_clean[:-3]
        
        response_clean = response_clean.strip()
        
        if response_clean.startswith('{'):
            data = json.loads(response_clean)
            
            # Extract raw data
            tips = data.get('tips', [])
            if isinstance(tips, str):
                tips = [tips]
            elif not isinstance(tips, list):
                tips = []
            
            rationale = data.get('rationale', 'No rationale provided')
            metric_overrides = data.get('metric_overrides')
            
            # Validate the response
            validation_result = validate_reasoning(tips, rationale, metric_overrides)
            
            # Log warnings if any
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    print(f"⚠️  Validation warning: {warning}")
            
            return ReasoningResponse(
                tips=validation_result.tips,
                rationale=validation_result.rationale,
                metric_overrides=validation_result.metric_overrides
            )
        
        # If not valid JSON, return fallback
        raise ValueError("Response is not valid JSON")
        
    except Exception as e:
        # Fallback response with empty tips
        return ReasoningResponse(
            tips=[],
            rationale=f"Analysis completed. (Parse error: {str(e)[:100]})"
        )

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        ollama_healthy = ollama_client.health_check()
        return jsonify({
            'status': 'healthy' if ollama_healthy else 'degraded',
            'ollama_connected': ollama_healthy,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/v1/reason', methods=['POST'])
def reason():
    """Main reasoning endpoint"""
    start_time = time.time()
    
    try:
        # Parse request
        request_json = request.get_json()
        if not request_json:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        reasoning_request = ReasoningRequest(
            dyad=request_json.get('dyad', ''),
            features=request_json.get('features', {}),
            context=request_json.get('context', {}),
            metrics=request_json.get('metrics', {}),
            history=request_json.get('history', [])
        )
        
        # Validate dyad
        if reasoning_request.dyad not in ['night', 'tantrum', 'meal']:
            return jsonify({'error': 'Invalid dyad. Must be night, tantrum, or meal'}), 400
        
        # Check cache first (if enabled)
        cache_hit = False
        if cache.is_enabled():
            cached_response = cache.get(
                reasoning_request.dyad,
                reasoning_request.features,
                reasoning_request.context,
                reasoning_request.metrics
            )
            
            if cached_response:
                cache_hit = True
                response_time = time.time() - start_time
                
                # Return cached response with cache hit header
                response = jsonify({
                    'tips': cached_response['tips'],
                    'rationale': cached_response['rationale'],
                    'metric_overrides': cached_response['metric_overrides'],
                    'response_time': round(response_time, 2),
                    'dyad': reasoning_request.dyad,
                    'cache_status': 'HIT'
                })
                response.headers['X-Reasoner-Cache'] = 'HIT'
                return response
        
        # Check Ollama availability
        if not ollama_client.health_check():
            return jsonify({'error': 'Ollama runtime not available'}), 503
        
        # Prepare messages for Ollama
        prompt = get_prompt(reasoning_request.dyad)
        
        # Build system message with strict JSON requirement
        system_message = f"""{prompt['system']}

Return ONLY JSON with keys: tips (array of ≤2 strings), rationale (string ≤140 chars), metric_overrides (object, optional). No prose, no markdown.

Constraints:
- Tips: ≤2 items, each ≤25 words
- Rationale: ≤140 characters
- Tone: {prompt['constraints']['tone']}
- Forbidden: {', '.join(prompt['constraints']['forbidden'])}"""

        user_message = prepare_user_message(reasoning_request)
        
        messages = [
            create_system_message(system_message),
            create_user_message(user_message)
        ]
        
        # Call Ollama
        ollama_response = ollama_client.post_chat(
            messages=messages,
            temperature=0.2,
            model="llama3.2:3b"
        )
        
        # Parse response
        reasoning_response = parse_ollama_response(ollama_response)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Cache the response (if enabled and not already cached)
        if cache.is_enabled() and not cache_hit:
            cache.set(
                reasoning_request.dyad,
                reasoning_request.features,
                reasoning_request.context,
                reasoning_request.metrics,
                {
                    'tips': reasoning_response.tips,
                    'rationale': reasoning_response.rationale,
                    'metric_overrides': reasoning_response.metric_overrides
                }
            )
        
        # Return response
        response = jsonify({
            'tips': reasoning_response.tips,
            'rationale': reasoning_response.rationale,
            'metric_overrides': reasoning_response.metric_overrides,
            'response_time': round(response_time, 2),
            'dyad': reasoning_request.dyad,
            'cache_status': 'HIT' if cache_hit else 'MISS'
        })
        
        # Set cache header
        if cache_hit:
            response.headers['X-Reasoner-Cache'] = 'HIT'
        else:
            response.headers['X-Reasoner-Cache'] = 'MISS'
        
        return response
        
    except Exception as e:
        response_time = time.time() - start_time
        return jsonify({
            'error': f'Reasoning failed: {str(e)}',
            'response_time': round(response_time, 2)
        }), 500

@app.route('/models', methods=['GET'])
def list_models():
    """List available Ollama models"""
    try:
        models = ollama_client.list_models()
        return jsonify({
            'models': models,
            'available': len(models) > 0
        })
    except Exception as e:
        return jsonify({'error': f'Failed to list models: {str(e)}'}), 500

@app.route('/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    try:
        stats = cache.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': f'Failed to get cache stats: {str(e)}'}), 500

@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the cache"""
    try:
        cache.clear()
        return jsonify({'message': 'Cache cleared successfully'})
    except Exception as e:
        return jsonify({'error': f'Failed to clear cache: {str(e)}'}), 500

if __name__ == '__main__':
    # Check Ollama availability on startup
    if not ollama_client.health_check():
        print("⚠️  Warning: Ollama runtime not available")
        print("   Make sure Ollama is running on http://localhost:11434")
        print("   Install with: curl -fsSL https://ollama.ai/install.sh | sh")
        print("   Pull model with: ollama pull gpt-oss-20b")
    else:
        print("✅ Ollama runtime connected")
    
    # Start Flask app
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True) 