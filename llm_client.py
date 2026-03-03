"""Cliente HTTP para LLM local con endpoint OpenAI-compatible."""

import json
import logging
import re
import time

import requests

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper HTTP al endpoint OpenAI-compatible de llama.cpp."""

    def __init__(
        self,
        endpoint: str = "http://127.0.0.1:8080/v1/chat/completions",
        timeout: int = 240,
        max_retries: int = 2,
        backoff_factor: float = 2.0,
    ):
        self.endpoint = endpoint
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def call(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> str:
        """Enviar prompt al LLM y devolver la respuesta como texto.

        Retry con backoff exponencial en errores de red/5xx.
        Raise en errores 4xx.
        """
        payload = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Content-Type": "application/json"}

        last_exc = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(
                    self.endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )

                if 400 <= resp.status_code < 500:
                    raise RuntimeError(
                        f"Error 4xx del LLM (no reintentable): {resp.status_code} - {resp.text}"
                    )

                resp.raise_for_status()

                data = resp.json()
                return data["choices"][0]["message"]["content"]

            except requests.exceptions.RequestException as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    wait = self.backoff_factor ** attempt
                    logger.warning(
                        "LLM request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        self.max_retries + 1,
                        wait,
                        exc,
                    )
                    time.sleep(wait)

        raise RuntimeError(f"LLM request failed after {self.max_retries + 1} attempts: {last_exc}")

    @staticmethod
    def parse_json_response(raw: str) -> dict | None:
        """Intentar parsear JSON de la respuesta del LLM.

        Quita fences ```json ... ``` si están presentes.
        """
        text = raw.strip()
        # Quitar fences de markdown
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def call_with_json_repair(
        self,
        system: str,
        user: str,
        fix_prompt_template: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> dict:
        """Llamar al LLM, parsear JSON, y si falla, intentar reparar.

        1. Llamar al LLM con system+user
        2. Intentar parsear JSON
        3. Si falla, mandar output roto al LLM con fix_prompt
        4. Si sigue fallando, raise
        """
        raw = self.call(system, user, temperature, max_tokens)
        logger.debug("LLM raw response (first 500 chars): %s", raw[:500])

        result = self.parse_json_response(raw)
        if result is not None:
            return result

        logger.warning("JSON parse failed, attempting repair...")
        fix_user = fix_prompt_template.replace("{broken_json}", raw)
        raw_fix = self.call(
            system="Sos un asistente que repara JSON malformado.",
            user=fix_user,
            temperature=0.1,
            max_tokens=max_tokens,
        )
        logger.debug("LLM fix response (first 500 chars): %s", raw_fix[:500])

        result = self.parse_json_response(raw_fix)
        if result is not None:
            return result

        raise RuntimeError(
            f"No se pudo obtener JSON válido del LLM después de reparación.\n"
            f"Respuesta original: {raw[:300]}\n"
            f"Respuesta reparación: {raw_fix[:300]}"
        )
