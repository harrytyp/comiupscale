#!/usr/bin/env python3
"""
vision_qa.py — Visual Quality Analysis for COMI HD Debug Loop

Sends a screenshot to MiMo V2.5 Vision (via OpenAI-compatible API)
and returns structured JSON with per-category quality ratings.

Usage:
    python3 scripts/vision_qa.py <screenshot_path> [--json-only]

Output (JSON to stdout):
    {
      "backgrounds": {"score": 8, "description": "..."},
      "costumes": {"score": 6, "description": "..."},
      "objects": {"score": 7, "description": "..."},
      "fonts": {"score": 9, "description": "..."},
      "overall": {"score": 7, "description": "..."},
      "raw_response": "...",
      "model": "mimo-v2.5"
    }
"""

import sys
import os
import json
import base64
import urllib.request
import urllib.error
import argparse
from pathlib import Path


# ── Configuration ──────────────────────────────────────────────────────────────
DEFAULT_API_BASE = "https://opencode.ai/zen/go/v1"
DEFAULT_MODEL = "mimo-v2.5"
REQUEST_TIMEOUT = 120  # seconds


def get_api_config():
    """Resolve API endpoint and key from environment variables."""
    api_key = os.environ.get("OPENCODE_GO_API_KEY", "")
    api_base = os.environ.get("OPENCODE_GO_BASE_URL", DEFAULT_API_BASE)

    if not api_key:
        # Try common fallback env var names
        for var in ("OPENAI_API_KEY", "OPENCODE_ZEN_API_KEY", "LLM_API_KEY"):
            api_key = os.environ.get(var, "")
            if api_key:
                break

    return api_key, api_base


def image_to_base64(image_path: str) -> str:
    """Read an image file and return its base64-encoded content."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_mime_type(image_path: str) -> str:
    """Determine MIME type from file extension."""
    ext = Path(image_path).suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".bmp": "image/bmp",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return mime_map.get(ext, "image/png")


VISION_PROMPT = """\
This is a screenshot from Curse of Monkey Island running with an HD texture mod.

Analyze the following visual quality categories and rate each 1-10 (10=perfect HD):

1) **Backgrounds**: Are they high-resolution (sharp, detailed, 2560x1920 native) or low-resolution (pixelated, blocky, stretched)?
2) **Costumes/Actors**: Are character costumes rendered in HD (smooth edges, detailed textures) or still original low-res 8-bit pixel art?
3) **Objects**: Are interactive objects/pickups HD (clean, detailed) or still original resolution?
4) **Fonts/Text**: Is on-screen text sharp and readable (HD font) or pixelated/blocky (original bitmap font)?
5) **Overall Quality**: General assessment of visual fidelity.

For each category, provide:
- A score (1-10)
- A brief description of what you observe

Respond in EXACTLY this JSON format (no markdown, no code fences):
{
  "backgrounds": {"score": <int>, "description": "<text>"},
  "costumes": {"score": <int>, "description": "<text>"},
  "objects": {"score": <int>, "description": "<text>"},
  "fonts": {"score": <int>, "description": "<text>"},
  "overall": {"score": <int>, "description": "<text>"}
}"""


def call_vision_api(image_path: str, api_key: str, api_base: str, model: str) -> dict:
    """Send image to the vision API and return parsed JSON response."""
    b64_image = image_to_base64(image_path)
    mime_type = get_mime_type(image_path)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_image}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.1,
    }

    url = f"{api_base.rstrip('/')}/chat/completions"
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        return {
            "error": f"HTTP {e.code}: {error_body[:500]}",
            "model": model,
        }
    except Exception as e:
        return {
            "error": f"Request failed: {str(e)}",
            "model": model,
        }

    try:
        response_json = json.loads(body)
    except json.JSONDecodeError:
        return {
            "error": f"Invalid JSON response: {body[:500]}",
            "model": model,
        }

    # Extract the assistant message content
    try:
        raw_content = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return {
            "error": f"Unexpected response structure: {body[:500]}",
            "model": model,
        }

    # Parse the vision analysis from the response
    return parse_vision_response(raw_content, model)


def parse_vision_response(raw_content: str, model: str) -> dict:
    """Parse the LLM response text into structured JSON."""
    # Try to extract JSON from the response (may be wrapped in code fences)
    text = raw_content.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (fences)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        analysis = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        import re
        json_match = re.search(r'\{[\s\S]*"backgrounds"[\s\S]*\}', text)
        if json_match:
            try:
                analysis = json.loads(json_match.group())
            except json.JSONDecodeError:
                # Return raw text as fallback
                return {
                    "backgrounds": {"score": 0, "description": "Parse error"},
                    "costumes": {"score": 0, "description": "Parse error"},
                    "objects": {"score": 0, "description": "Parse error"},
                    "fonts": {"score": 0, "description": "Parse error"},
                    "overall": {"score": 0, "description": "Parse error"},
                    "raw_response": raw_content,
                    "model": model,
                    "parse_error": True,
                }
        else:
            return {
                "backgrounds": {"score": 0, "description": "Parse error"},
                "costumes": {"score": 0, "description": "Parse error"},
                "objects": {"score": 0, "description": "Parse error"},
                "fonts": {"score": 0, "description": "Parse error"},
                "overall": {"score": 0, "description": "Parse error"},
                "raw_response": raw_content,
                "model": model,
                "parse_error": True,
            }

    # Ensure all required keys exist
    for key in ("backgrounds", "costumes", "objects", "fonts", "overall"):
        if key not in analysis:
            analysis[key] = {"score": 0, "description": f"Missing category: {key}"}
        elif "score" not in analysis[key]:
            analysis[key]["score"] = 0
        elif "description" not in analysis[key]:
            analysis[key]["description"] = ""

    analysis["raw_response"] = raw_content
    analysis["model"] = model
    return analysis


def main():
    parser = argparse.ArgumentParser(
        description="Visual Quality Analysis for COMI HD screenshots"
    )
    parser.add_argument("screenshot", help="Path to screenshot image file")
    parser.add_argument("--json-only", action="store_true",
                        help="Output only JSON (no human-readable text)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Vision model name (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    # Validate input
    if not os.path.isfile(args.screenshot):
        print(json.dumps({"error": f"File not found: {args.screenshot}"}))
        sys.exit(1)

    # Get API config
    api_key, api_base = get_api_config()
    if not api_key:
        print(json.dumps({
            "error": "No API key found. Set OPENCODE_GO_API_KEY or OPENAI_API_KEY.",
            "model": args.model,
        }))
        sys.exit(1)

    # Call vision API
    result = call_vision_api(args.screenshot, api_key, api_base, args.model)

    if not args.json_only:
        # Human-readable output to stderr
        if "error" in result:
            print(f"[vision_qa] ERROR: {result['error']}", file=sys.stderr)
        else:
            print(f"[vision_qa] Analysis for: {args.screenshot}", file=sys.stderr)
            for cat in ("backgrounds", "costumes", "objects", "fonts", "overall"):
                info = result.get(cat, {})
                score = info.get("score", "?")
                desc = info.get("description", "")
                print(f"  {cat:>12}: {score}/10 — {desc}", file=sys.stderr)
            print(file=sys.stderr)

    # JSON to stdout (always)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
