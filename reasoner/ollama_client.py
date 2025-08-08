#!/usr/bin/env python3
"""
Ollama client for Silli's reasoning engine
Handles communication with local Ollama runtime
"""

import json
import os
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class OllamaMessage:
    role: str  # "system", "user", "assistant"
    content: str

@dataclass
class OllamaChatRequest:
    model: str
    messages: List[OllamaMessage]
    temperature: float = 0.2
    stream: bool = False

@dataclass
class OllamaChatResponse:
    model: str
    created_at: str
    message: OllamaMessage
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None

class OllamaClient:
    def __init__(self, host: Optional[str] = None):
        """Initialize Ollama client with host URL"""
        self.host = host or os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.base_url = f"{self.host}/api"
        
    def post_chat(self, messages: List[OllamaMessage], temperature: float = 0.2, model: str = "gpt-oss:20b") -> str:
        """
        Send chat completion request to Ollama
        
        Args:
            messages: List of messages with role and content
            temperature: Sampling temperature (0.0-1.0)
            model: Model name to use
            
        Returns:
            Assistant's response content as string
        """
        try:
            # Prepare request
            request_data = {
                "model": model,
                "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
                "temperature": temperature,
                "stream": False
            }
            
            # Send request
            url = f"{self.base_url}/chat"
            timeout = int(os.getenv('REASONER_TIMEOUT', 60))  # Use configurable timeout, default 60s
            response = requests.post(url, json=request_data, timeout=timeout)
            
            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
            
            # Parse response
            response_data = response.json()
            
            # Extract assistant message content
            if 'message' in response_data and 'content' in response_data['message']:
                return response_data['message']['content']
            else:
                raise Exception("Invalid response format from Ollama")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error communicating with Ollama: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response from Ollama: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error in Ollama client: {e}")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models"""
        try:
            url = f"{self.base_url}/tags"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                raise Exception(f"Failed to list models: {response.status_code}")
            
            data = response.json()
            return data.get('models', [])
            
        except Exception as e:
            raise Exception(f"Error listing models: {e}")
    
    def health_check(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            url = f"{self.base_url}/tags"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False

# Convenience function for creating messages
def create_system_message(content: str) -> OllamaMessage:
    """Create a system message"""
    return OllamaMessage(role="system", content=content)

def create_user_message(content: str) -> OllamaMessage:
    """Create a user message"""
    return OllamaMessage(role="user", content=content)

def create_assistant_message(content: str) -> OllamaMessage:
    """Create an assistant message"""
    return OllamaMessage(role="assistant", content=content) 