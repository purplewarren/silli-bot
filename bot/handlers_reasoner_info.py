#!/usr/bin/env python3
"""
Reasoner info handlers for Silli Bot
Provides visibility into reasoner model status and performance
"""

import aiohttp
import os
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from loguru import logger
from .i18n import get_locale

router_reasoner_info = Router()

REASONER_BASE_URL = os.getenv('REASONER_BASE_URL', 'http://localhost:5001')

@router_reasoner_info.message(Command("reason_model"))
async def handle_reason_model_command(message: Message):
    """Show reasoner model status and configuration"""
    locale = get_locale(message.chat.id)
    
    try:
        # Get reasoner status
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{REASONER_BASE_URL}/status", timeout=5) as response:
                if response.status == 200:
                    status = await response.json()
                    
                    # Format response based on locale
                    if locale == "pt_br":
                        text = "🧠 **Status do Modelo de IA**\n\n"
                        
                        # Check for low-fidelity mode
                        model_hint = status.get('model_hint', 'N/A')
                        model_used = status.get('last_model_used', 'Nenhum')
                        if model_used != model_hint and model_used != 'Nenhum':
                            text += "🔶 **MODO DE BAIXA FIDELIDADE**\n\n"
                        
                        text += f"**Ativo**: {'✅ Sim' if status.get('enabled') else '❌ Não'}\n"
                        text += f"**Modelo Sugerido**: `{model_hint}`\n"
                        text += f"**Último Modelo Usado**: `{model_used}`\n"
                        text += f"**Permite Fallback**: {'✅ Sim' if status.get('allow_fallback') else '❌ Não'}\n"
                        text += f"**Taxa de Cache**: {status.get('cache_hit_rate', 0) * 100:.1f}%\n"
                        text += f"**Endpoint**: `{status.get('endpoint_host', 'unknown')}`\n"
                        
                        if status.get('fallback_occurred'):
                            text += f"\n⚠️ **Fallback Ocorreu**: {status.get('fallback_reason', 'Motivo desconhecido')}"
                        
                        cache_stats = status.get('cache_stats', {})
                        if cache_stats.get('enabled'):
                            text += f"\n\n📊 **Estatísticas do Cache**:\n"
                            text += f"• Acertos: {cache_stats.get('hits', 0)}\n"
                            text += f"• Perdas: {cache_stats.get('misses', 0)}\n"
                            text += f"• Tamanho: {cache_stats.get('size', 0)}"
                    else:
                        text = "🧠 **AI Model Status**\n\n"
                        
                        # Check for low-fidelity mode
                        model_hint = status.get('model_hint', 'N/A')
                        model_used = status.get('last_model_used', 'None')
                        if model_used != model_hint and model_used != 'None':
                            text += "🔶 **LOW-FIDELITY MODE**\n\n"
                        
                        text += f"**Enabled**: {'✅ Yes' if status.get('enabled') else '❌ No'}\n"
                        text += f"**Model Hint**: `{model_hint}`\n"
                        text += f"**Last Model Used**: `{model_used}`\n"
                        text += f"**Allow Fallback**: {'✅ Yes' if status.get('allow_fallback') else '❌ No'}\n"
                        text += f"**Cache Hit Rate**: {status.get('cache_hit_rate', 0) * 100:.1f}%\n"
                        text += f"**Endpoint**: `{status.get('endpoint_host', 'unknown')}`\n"
                        
                        if status.get('fallback_occurred'):
                            text += f"\n⚠️ **Fallback Occurred**: {status.get('fallback_reason', 'Unknown reason')}"
                        
                        cache_stats = status.get('cache_stats', {})
                        if cache_stats.get('enabled'):
                            text += f"\n\n📊 **Cache Stats**:\n"
                            text += f"• Hits: {cache_stats.get('hits', 0)}\n"
                            text += f"• Misses: {cache_stats.get('misses', 0)}\n"
                            text += f"• Size: {cache_stats.get('size', 0)}"
                
                else:
                    if locale == "pt_br":
                        text = f"❌ Erro ao obter status do modelo (HTTP {response.status})"
                    else:
                        text = f"❌ Failed to get model status (HTTP {response.status})"
                        
    except aiohttp.ClientTimeout:
        if locale == "pt_br":
            text = "⏱️ Timeout ao conectar com o serviço de IA"
        else:
            text = "⏱️ Timeout connecting to AI service"
    except Exception as e:
        logger.error(f"Error getting reasoner status: {e}")
        if locale == "pt_br":
            text = f"❌ Erro ao obter status: {str(e)}"
        else:
            text = f"❌ Error getting status: {str(e)}"
    
    await message.reply(text, parse_mode="Markdown")

@router_reasoner_info.message(Command("reason_models"))
async def handle_reason_models_command(message: Message):
    """List available AI models"""
    locale = get_locale(message.chat.id)
    
    try:
        # Get available models
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{REASONER_BASE_URL}/models", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get('models', [])
                    
                    if locale == "pt_br":
                        text = "🤖 **Modelos de IA Disponíveis**\n\n"
                        if models:
                            for model in models:
                                name = model.get('name', 'Unknown')
                                size = model.get('size', 0)
                                size_gb = round(size / (1024**3), 1) if size else 0
                                text += f"• `{name}` ({size_gb} GB)\n"
                        else:
                            text += "Nenhum modelo disponível"
                    else:
                        text = "🤖 **Available AI Models**\n\n"
                        if models:
                            for model in models:
                                name = model.get('name', 'Unknown')
                                size = model.get('size', 0)
                                size_gb = round(size / (1024**3), 1) if size else 0
                                text += f"• `{name}` ({size_gb} GB)\n"
                        else:
                            text += "No models available"
                
                else:
                    if locale == "pt_br":
                        text = f"❌ Erro ao listar modelos (HTTP {response.status})"
                    else:
                        text = f"❌ Failed to list models (HTTP {response.status})"
                        
    except aiohttp.ClientTimeout:
        if locale == "pt_br":
            text = "⏱️ Timeout ao conectar com o serviço de IA"
        else:
            text = "⏱️ Timeout connecting to AI service"
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        if locale == "pt_br":
            text = f"❌ Erro ao listar modelos: {str(e)}"
        else:
            text = f"❌ Error listing models: {str(e)}"
    
    await message.reply(text, parse_mode="Markdown")
