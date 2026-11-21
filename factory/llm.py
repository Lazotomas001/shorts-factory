"""Optional: free-tier LLM to suggest new quiz questions (any OpenAI-compatible API).

Examples (all have free tiers; check their current limits):
  Google Gemini : LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai  LLM_MODEL=gemini-2.5-flash
  Groq          : LLM_BASE_URL=https://api.groq.com/openai/v1                          LLM_MODEL=llama-3.3-70b-versatile
  OpenRouter    : LLM_BASE_URL=https://openrouter.ai/api/v1                              LLM_MODEL=<any ':free' model>
Set LLM_API_KEY too. Without these the pipeline still works from the built-in banks.
"""
import json
import os
import urllib.request


def chat(prompt, temperature=0.8):
    base, key, model = (os.environ.get(k) for k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))
    if not (base and key and model):
        raise RuntimeError("Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL to use an LLM.")
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                                 data=json.dumps({"model": model, "temperature": temperature,
                                                  "messages": [{"role": "user", "content": prompt}]}).encode())
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def quiz_questions(n, avoid):
    prompt = (f"Write {n} multiple-choice general-knowledge trivia questions for a YouTube Shorts quiz. "
              "Each must have ONE unambiguous, well-established correct answer and 3 plausible wrong answers. "
              "Keep questions under 80 characters and answers under 25 characters. Avoid these topics/questions: "
              + "; ".join(avoid[:60]) +
              '\nReturn ONLY a JSON array of objects: {"q": str, "a": str, "w": [str, str, str], "cat": str}')
    text = chat(prompt)
    text = text[text.find("["): text.rfind("]") + 1]
    return json.loads(text)
