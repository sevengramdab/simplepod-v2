#!/usr/bin/env python3
"""
core/unified/llm_fallback.py
===========================
Zero-signup LLM fallback for when local Ollama is down or unavailable.
Uses Pollinations.AI — completely free, no API key, no registration.

ELI5: If the building's main generator (Ollama) goes offline,
      this is the backup solar array that kicks in automatically.
      No utility company account needed. Just sunshine and panels.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Optional

logger = logging.getLogger("simplepod.unified.llm_fallback")

# Pollinations.AI — free, open, no signup required
POLLINATIONS_URL = "https://text.pollinations.ai/"
DEFAULT_MODEL = "openai"


def query_pollinations(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system_prompt: Optional[str] = None,
    timeout: int = 60,
) -> str:
    """
    ELI5: Send a message via the free public radio channel.
          Anyone can use it. No license required.
    """
    # Build the prompt with system context if provided
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n{prompt}"

    # Pollinations accepts the prompt as a URL path or POST body
    # Using POST for longer prompts
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt or "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        "model": model,
        "seed": 42,
        "jsonMode": False,
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "SimplePod-Unified/2.6",
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://text.pollinations.ai/",
            data=data,
            method="POST",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = resp.read().decode("utf-8", errors="replace")
            logger.info("Pollinations responded (%d chars)", len(result))
            return result.strip()
    except Exception as exc:
        logger.warning("Pollinations POST failed: %s", exc)
        # Fallback to GET for simple prompts
        try:
            encoded = urllib.parse.quote(prompt[:2000])  # URL length limit
            url = f"{POLLINATIONS_URL}{encoded}?model={model}&seed=42"
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": "SimplePod-Unified/2.6"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = resp.read().decode("utf-8", errors="replace")
                return result.strip()
        except Exception as exc2:
            logger.error("Pollinations GET also failed: %s", exc2)
            return ""


def query_llm_with_fallback(
    prompt: str,
    ollama_host: str = "http://127.0.0.1:11434",
    ollama_model: str = "llama3.2",
    system_prompt: Optional[str] = None,
    timeout: int = 60,
) -> str:
    """
    ELI5: Try the main generator first. If it's dead, flip the
          automatic transfer switch to solar backup. Zero downtime.
    """
    # Try Ollama first
    try:
        payload = {
            "model": ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{ollama_host}/api/chat",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            content = result.get("message", {}).get("content", "")
            if content.strip():
                logger.info("Ollama responded successfully")
                return content.strip()
    except Exception as exc:
        logger.warning("Ollama unavailable (%s), falling back to Pollinations", exc)

    # Fallback to Pollinations
    return query_pollinations(prompt, system_prompt=system_prompt, timeout=timeout)


# Convenience aliases
ask = query_llm_with_fallback
fix_code = lambda prompt: query_llm_with_fallback(
    prompt,
    system_prompt="You are an expert Python developer. Return only corrected code inside a ```python block. No explanations."
)
