"""OCR via NVIDIA NIM API (Qwen 3.5 Vision).

API: https://build.nvidia.com/qwen/qwen3.5-122b-a10ba
Key: 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
"""

import base64
import json
import os
import urllib.request

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_API_KEY = "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"
NVIDIA_MODEL = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")

PROMPT_OCR = """Extraia TODO o texto manuscrito visível nesta imagem de justificativa de prova.
Retorne APENAS o texto extraído, palavra por palavra, exatamente como aparece na imagem.
Preserve a formatação, parágrafos e quebras de linha.
Se houver equações, descreva-as em texto.
Não adicione comentários, explicações ou markdown."""


def _encode_image(image_path):
    """Read image file and encode as base64 data URL."""
    if not os.path.isfile(image_path):
        return None
    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png"}
    mime = mime_map.get(ext, "jpeg")
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/{mime};base64,{data}"


def extract_text(image_path, prompt=None):
    """Extract text from an image using NVIDIA NIM API."""
    if not os.path.isfile(image_path):
        return ""

    b64 = _encode_image(image_path)
    if not b64:
        return ""

    if prompt is None:
        prompt = PROMPT_OCR

    payload = {
        "model": NVIDIA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": b64}},
                ],
            }
        ],
        "max_tokens": 2000,
        "temperature": 0.1,
    }

    req = urllib.request.Request(
        NVIDIA_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            msg = result.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning_content") or ""
            return content.strip()
    except Exception as e:
        return f"[OCR error: {e}]"


def extract_all_texts(image_paths):
    """Extract text from multiple images."""
    texts = []
    for path in image_paths:
        text = extract_text(path)
        if text:
            texts.append(text)
    return "\n".join(texts)


def compare_justifications(image1_path, image2_path):
    """Compare two justification images using NVIDIA API for detailed analysis."""
    if not os.path.isfile(image1_path) or not os.path.isfile(image2_path):
        return {"similarity": 0, "analysis": "Imagens não encontradas"}

    b64_1 = _encode_image(image1_path)
    b64_2 = _encode_image(image2_path)
    if not b64_1 or not b64_2:
        return {"similarity": 0, "analysis": "Erro ao codificar imagens"}

    prompt = """Compare estas duas imagens de justificativas manuscritas de prova.
Analise:
1. O conteúdo do texto é igual ou muito similar? (0-100%)
2. A caligrafia parece ser da mesma pessoa?
3. Há evidências de cópia (mesmos erros, mesma estrutura)?

Responda em JSON:
{"similarity": <0-100>, "same_handwriting": <true/false>, "analysis": "<explicação curta em português>"}"""

    payload = {
        "model": NVIDIA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": b64_1}},
                    {"type": "image_url", "image_url": {"url": b64_2}},
                ],
            }
        ],
        "max_tokens": 500,
        "temperature": 0.1,
    }

    req = urllib.request.Request(
        NVIDIA_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            msg = result.get("choices", [{}])[0].get("message", {})
            content = msg.get("content") or msg.get("reasoning_content") or ""
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"similarity": 0, "analysis": content}
    except Exception as e:
        return {"similarity": 0, "analysis": f"Erro: {e}"}
