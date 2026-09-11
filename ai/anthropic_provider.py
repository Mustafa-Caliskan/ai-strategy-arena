"""
anthropic_provider.py — Backward compatibility wrapper for ClaudeProvider
Directly exposes ClaudeProvider and AnthropicProvider.
"""
from __future__ import annotations
from ai.claude_provider import ClaudeProvider, AnthropicProvider, DEFAULT_CLAUDE_MODEL

__all__ = ["ClaudeProvider", "AnthropicProvider", "DEFAULT_CLAUDE_MODEL"]
