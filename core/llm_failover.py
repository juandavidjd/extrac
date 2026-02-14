#!/usr/bin/env python3
"""
ODI LLM Failover Chain v1.0
===========================
Cadena de failover centralizada para todos los servicios ODI.

Orden de prioridad:
  1. Gemini 1.5 Pro (Google) - Rapido, economico
  2. GPT-4o (OpenAI) - Preciso, multimodal
  3. Claude Sonnet (Anthropic) - Razonamiento profundo
  4. Groq (Llama) - Ultra-rapido, fallback
  5. Lobotomy - Respuestas predefinidas (ultimo recurso)

Uso:
    from llm_failover import LLMFailover

    llm = LLMFailover()
    response = llm.generate("Que llanta sirve para BWS 125?")
    response = llm.generate_with_image("Extrae productos", image_b64)
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("llm_failover")


class Provider(Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    CLAUDE = "claude"
    GROQ = "groq"
    LOBOTOMY = "lobotomy"


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    latency_ms: int
    tokens_used: int = 0
    fallback_chain: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "provider": self.provider,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "tokens_used": self.tokens_used,
            "fallback_chain": self.fallback_chain
        }


class LLMFailover:
    DEFAULT_CHAIN = [
        Provider.GEMINI,
        Provider.OPENAI,
        Provider.CLAUDE,
        Provider.GROQ,
        Provider.LOBOTOMY
    ]

    LOBOTOMY_RESPONSES = {
        "default": "Disculpa, estoy teniendo dificultades tecnicas. Por favor intenta de nuevo en unos minutos o contacta a soporte.",
        "saludo": "Hola! Bienvenido a ODI. En que puedo ayudarte hoy?",
        "precio": "Para consultar precios actualizados, por favor contacta directamente al vendedor.",
        "disponibilidad": "Para confirmar disponibilidad, te recomiendo contactar directamente a la tienda.",
        "horario": "Nuestro horario de atencion es de lunes a sabado, 8am a 6pm.",
    }

    def __init__(self, chain: List[Provider] = None, timeout: int = 30, system_prompt: str = None):
        self.chain = chain or self.DEFAULT_CHAIN
        self.timeout = timeout
        self.system_prompt = system_prompt or "Eres un asistente experto en repuestos de motos. Responde de forma concisa y util."
        self._load_env()
        self._clients: Dict[Provider, Any] = {}

    def _load_env(self):
        from dotenv import load_dotenv
        load_dotenv("/opt/odi/.env")
        self.api_keys = {
            Provider.GEMINI: os.getenv("GEMINI_API_KEY"),
            Provider.OPENAI: os.getenv("OPENAI_API_KEY"),
            Provider.CLAUDE: os.getenv("ANTHROPIC_API_KEY"),
            Provider.GROQ: os.getenv("GROQ_API_KEY"),
        }

    def _get_gemini_client(self):
        if Provider.GEMINI not in self._clients:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_keys[Provider.GEMINI])
                self._clients[Provider.GEMINI] = genai.GenerativeModel("gemini-2.0-flash")
            except Exception as e:
                log.warning(f"Failed to init Gemini: {e}")
                return None
        return self._clients.get(Provider.GEMINI)

    def _get_openai_client(self):
        if Provider.OPENAI not in self._clients:
            try:
                from openai import OpenAI
                self._clients[Provider.OPENAI] = OpenAI(api_key=self.api_keys[Provider.OPENAI], timeout=self.timeout)
            except Exception as e:
                log.warning(f"Failed to init OpenAI: {e}")
                return None
        return self._clients.get(Provider.OPENAI)

    def _get_claude_client(self):
        if Provider.CLAUDE not in self._clients:
            try:
                import anthropic
                self._clients[Provider.CLAUDE] = anthropic.Anthropic(api_key=self.api_keys[Provider.CLAUDE], timeout=self.timeout)
            except Exception as e:
                log.warning(f"Failed to init Claude: {e}")
                return None
        return self._clients.get(Provider.CLAUDE)

    def _get_groq_client(self):
        if Provider.GROQ not in self._clients:
            try:
                from groq import Groq
                self._clients[Provider.GROQ] = Groq(api_key=self.api_keys[Provider.GROQ])
            except Exception as e:
                log.warning(f"Failed to init Groq: {e}")
                return None
        return self._clients.get(Provider.GROQ)

    def _call_gemini(self, prompt: str, image_b64: str = None) -> Tuple[str, str, int]:
        client = self._get_gemini_client()
        if not client:
            raise Exception("Gemini client not available")
        start = datetime.now()
        if image_b64:
            import base64
            image_data = base64.b64decode(image_b64)
            response = client.generate_content([prompt, {"mime_type": "image/png", "data": image_data}])
        else:
            response = client.generate_content(prompt)
        latency = int((datetime.now() - start).total_seconds() * 1000)
        return response.text, "gemini-2.0-flash", latency

    def _call_openai(self, prompt: str, image_b64: str = None) -> Tuple[str, str, int]:
        client = self._get_openai_client()
        if not client:
            raise Exception("OpenAI client not available")
        start = datetime.now()
        model = "gpt-4o"
        messages = [{"role": "system", "content": self.system_prompt}]
        if image_b64:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                ]
            })
        else:
            messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(model=model, messages=messages, temperature=0.3, max_tokens=2048)
        latency = int((datetime.now() - start).total_seconds() * 1000)
        return response.choices[0].message.content, model, latency

    def _call_claude(self, prompt: str, image_b64: str = None) -> Tuple[str, str, int]:
        client = self._get_claude_client()
        if not client:
            raise Exception("Claude client not available")
        start = datetime.now()
        model = "claude-sonnet-4-20250514"
        content = []
        if image_b64:
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}})
        content.append({"type": "text", "text": prompt})
        response = client.messages.create(model=model, max_tokens=2048, system=self.system_prompt, messages=[{"role": "user", "content": content}])
        latency = int((datetime.now() - start).total_seconds() * 1000)
        text = response.content[0].text if response.content else ""
        return text, model, latency

    def _call_groq(self, prompt: str, image_b64: str = None) -> Tuple[str, str, int]:
        client = self._get_groq_client()
        if not client:
            raise Exception("Groq client not available")
        start = datetime.now()
        model = "llama-3.3-70b-versatile"
        if image_b64:
            prompt = f"[NOTA: Se adjunto una imagen que no puedo procesar]\n\n{prompt}"
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": self.system_prompt}, {"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=2048
        )
        latency = int((datetime.now() - start).total_seconds() * 1000)
        return response.choices[0].message.content, model, latency

    def _call_lobotomy(self, prompt: str, image_b64: str = None) -> Tuple[str, str, int]:
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["hola", "buenos", "buenas", "hey"]):
            response = self.LOBOTOMY_RESPONSES["saludo"]
        elif any(w in prompt_lower for w in ["precio", "cuesta", "vale", "costo"]):
            response = self.LOBOTOMY_RESPONSES["precio"]
        elif any(w in prompt_lower for w in ["disponible", "hay", "tienen", "stock"]):
            response = self.LOBOTOMY_RESPONSES["disponibilidad"]
        elif any(w in prompt_lower for w in ["horario", "abren", "cierran", "hora"]):
            response = self.LOBOTOMY_RESPONSES["horario"]
        else:
            response = self.LOBOTOMY_RESPONSES["default"]
        return response, "lobotomy-v1", 0

    def generate(self, prompt: str, image_b64: str = None, preferred_provider: Provider = None) -> LLMResponse:
        chain = self.chain.copy()
        if preferred_provider and preferred_provider in chain:
            chain.remove(preferred_provider)
            chain.insert(0, preferred_provider)

        fallback_chain = []
        last_error = None

        provider_methods = {
            Provider.GEMINI: self._call_gemini,
            Provider.OPENAI: self._call_openai,
            Provider.CLAUDE: self._call_claude,
            Provider.GROQ: self._call_groq,
            Provider.LOBOTOMY: self._call_lobotomy,
        }

        for provider in chain:
            fallback_chain.append(provider.value)
            if provider != Provider.LOBOTOMY and not self.api_keys.get(provider):
                log.warning(f"[{provider.value}] No API key, skipping")
                continue
            try:
                log.info(f"[{provider.value}] Attempting call...")
                method = provider_methods[provider]
                content, model, latency = method(prompt, image_b64)
                log.info(f"[{provider.value}] Success in {latency}ms")
                return LLMResponse(content=content, provider=provider.value, model=model, latency_ms=latency, fallback_chain=fallback_chain)
            except Exception as e:
                last_error = str(e)
                log.warning(f"[{provider.value}] Failed: {last_error}")
                continue

        return LLMResponse(
            content=f"Error: Todos los proveedores fallaron. Ultimo error: {last_error}",
            provider="error", model="none", latency_ms=0, fallback_chain=fallback_chain
        )

    def generate_with_image(self, prompt: str, image_b64: str) -> LLMResponse:
        return self.generate(prompt, image_b64=image_b64)

    def test_all_providers(self) -> Dict[str, Any]:
        results = {}
        test_prompt = "Responde solo con: OK"
        for provider in Provider:
            try:
                if provider == Provider.LOBOTOMY:
                    results[provider.value] = {"status": "available", "type": "fallback"}
                    continue
                if not self.api_keys.get(provider):
                    results[provider.value] = {"status": "no_api_key"}
                    continue
                response = self.generate(test_prompt, preferred_provider=provider)
                if response.provider == provider.value:
                    results[provider.value] = {"status": "ok", "model": response.model, "latency_ms": response.latency_ms}
                else:
                    results[provider.value] = {"status": "failed_to_preferred"}
            except Exception as e:
                results[provider.value] = {"status": "error", "error": str(e)}
        return results


if __name__ == "__main__":
    import sys
    llm = LLMFailover()
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Testing all providers...")
        results = llm.test_all_providers()
        print(json.dumps(results, indent=2))
    else:
        prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Que llanta sirve para una BWS 125?"
        print(f"Prompt: {prompt}\n")
        response = llm.generate(prompt)
        print(f"Provider: {response.provider}")
        print(f"Model: {response.model}")
        print(f"Latency: {response.latency_ms}ms")
        print(f"Chain: {response.fallback_chain}")
        print(f"\nResponse:\n{response.content}")
