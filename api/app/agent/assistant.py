"""The study's donation assistant.

One loop, four engines:
  * openai:    ChatGPT via the OpenAI API (set OPENAI_API_KEY and OPENAI_MODEL);
               OPENAI_BASE_URL also points it at OpenAI-compatible providers
  * anthropic: Claude via the Anthropic API (set ANTHROPIC_API_KEY)
  * ollama:    a local model through Ollama's /api/chat tool calling
  * rules:     deterministic keyword planner, so the flow never dead-ends

For a study, run every participant on the same engine: set AGENT_PROVIDER.
The engine, model and PROMPT_VERSION are logged on every turn.

`run()` yields events the frontend renders live:
  {"type": "start", "engine", "model"}
  {"type": "step", "tool", "labelAr", "labelEn", "input"}
  {"type": "ui", "block": {...}}
  {"type": "text", "text"}
  {"type": "error", "message"}
  {"type": "done", "engine", "model"}
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Iterator
from datetime import datetime

import httpx

from .tools import TOOLS, ToolContext, dumps, execute, ground_cards

NOW = datetime(2026, 9, 24)
MAX_STEPS = 12

ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5-5")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "")          # no default: pick one from your OpenAI dashboard
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL") or None
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b-instruct-2507-q4_K_M")

SYSTEM = """You are the donation assistant in a research study about how people choose charity campaigns.
Each participant has a wallet of VIRTUAL riyals (not real money) to allocate to campaigns they choose.
Your job is to help them discover campaigns that match what they care about, understand them, and
decide how to allocate — as a helpful, neutral guide.

Neutrality matters: the study measures participants' own choices.
- Present options with honest trade-offs. Do not steer toward particular campaigns, charities or causes
  beyond what the participant asks for, and never pressure, guilt or rush them.
- If they ask for your opinion, give one with reasons grounded in the data, and say the choice is theirs.
- Never ask for personal information (real name, contact details, exact location, health, finances).
  If they share some, do not repeat it back.

How to work
- If a missing detail would change your answer materially, ask ONE short question; otherwise proceed and
  state your assumption briefly.
- Fetch before you speak. Every campaign, number, charity fact and update you mention must come from a tool
  result in this conversation. Never invent campaigns, figures or ratings.
- Typical flow: search_campaigns → get_campaign_details / get_charity_profile for serious candidates →
  estimate_impact when an amount is discussed → show_campaigns for every campaign you suggest (2–4).
  Use show_comparison when they weigh options. Use get_wallet to know their balance, and
  propose_allocation only when they ask for help splitting it.
- You cannot move money. Participants allocate themselves from the cards or your proposal.

Zakat and waqf
- "I have 2000 riyals of zakat" means that amount IS the zakat to give: do not recalculate it.
  zakat_calculator is only for "how much zakat do I owe?" from total wealth.
- For zakat, only suggest zakat_eligible campaigns and mention the zakat category given by the charity.
  Nisab uses an approximate gold price; say so. Do not issue religious rulings.
- Waqf preserves the principal and spends its yield indefinitely (صدقة جارية / ongoing charity).

Style
- Reply in {language}. Warm, respectful, concise: at most ~120 words of prose; the cards carry the details.
- Amounts are virtual riyals: write "300 ريال افتراضي" in Arabic or "300 virtual SAR" in English.
- Use campaign titles exactly as the tools return them, never ids.
- In Arabic, spell religious terms exactly (زكاة، صدقة، صدقة جارية، وقف، نصاب) and do not add diacritics."""

PROMPT_VERSION = "study-v1-" + hashlib.sha1(
    (SYSTEM + json.dumps({n: t["description"] for n, t in TOOLS.items()}, sort_keys=True)).encode()).hexdigest()[:8]

LANG_NAME = {"ar": "Modern Standard Arabic", "en": "English"}


def _system(lang: str) -> str:
    return SYSTEM.replace("{language}", LANG_NAME.get(lang, "Arabic"))


def _context_note(ctx: ToolContext, remaining: float) -> str:
    return (f"[context] Today {NOW:%Y-%m-%d} | Participant language: {LANG_NAME.get(ctx.lang)} | "
            f"Virtual wallet: {ctx.wallet:.0f}, remaining {remaining:.0f}")


def available_engines() -> dict:
    ollama, installed = False, []
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=1.5)
        installed = [m["name"] for m in r.json().get("models", [])]
        ollama = OLLAMA_MODEL in installed or f"{OLLAMA_MODEL}:latest" in installed
    except Exception:
        pass
    return {
        "openai": bool(os.environ.get("OPENAI_API_KEY") and OPENAI_MODEL),
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")),
        "ollama": ollama, "rules": True,
        "models": {"openai": OPENAI_MODEL, "anthropic": ANTHROPIC_MODEL, "ollama": OLLAMA_MODEL},
        "ollamaInstalled": installed,
    }


def pick_engine() -> str:
    avail = available_engines()
    pref = os.environ.get("AGENT_PROVIDER", "auto")
    if pref in ENGINES and avail[pref]:
        return pref
    for e in ("openai", "anthropic", "ollama"):
        if avail[e]:
            return e
    return "rules"


def model_for(engine: str) -> str | None:
    return {"openai": OPENAI_MODEL, "anthropic": ANTHROPIC_MODEL, "ollama": OLLAMA_MODEL}.get(engine)


_T = "[\\u064B-\\u0652]*"
_MISSPELT_SADAQAH = re.compile("(?<![\\w\\u0640])س" + _T + "د" + _T + "ق" + _T + "[ةه]" + _T
                               + "(?:\\s+ج" + _T + "ا" + _T + "ر" + _T + "ي" + _T + "[ةه]" + _T + ")?(?![\\w\\u0640])")


def _polish(text: str) -> str:
    """Correct «سدقة», a frequent small-model misspelling of صدقة."""
    return _MISSPELT_SADAQAH.sub(lambda m: "صدقة جارية" if "ج" in m.group(0) else "صدقة", text)


def _flush(ctx: ToolContext) -> Iterator[dict]:
    while ctx.ui_blocks:
        yield {"type": "ui", "block": ctx.ui_blocks.pop(0)}


def _call_tool(ctx: ToolContext, name: str, args: dict) -> Iterator[dict]:
    spec = TOOLS.get(name, {})
    yield {"type": "step", "tool": name, "labelAr": spec.get("label_ar", name),
           "labelEn": spec.get("label_en", name), "input": args}
    result = execute(ctx, name, args)
    yield from _flush(ctx)
    return result


# -------------------------------------------------------------- Anthropic
def _run_anthropic(ctx, message, history, remaining) -> Iterator[dict]:
    import anthropic

    client = anthropic.Anthropic()
    tools = [{"name": n, "description": t["description"], "input_schema": t["schema"]} for n, t in TOOLS.items()]
    messages = [*({"role": h["role"], "content": h["content"]} for h in history if h.get("content")),
                {"role": "user", "content": f"{_context_note(ctx, remaining)}\n\n{message}"}]
    extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

    for _ in range(MAX_STEPS):
        try:
            resp = client.beta.messages.create(
                model=ANTHROPIC_MODEL, max_tokens=16000, system=_system(ctx.lang),
                thinking={"type": "adaptive"}, tools=tools, messages=messages, **extra)
        except anthropic.BadRequestError as e:
            if extra and "fallback" in str(e).lower():
                extra = {}
                continue
            raise
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason == "refusal":
            yield {"type": "text", "text": "عذراً، لا أستطيع المساعدة في هذا الطلب." if ctx.lang == "ar"
                   else "Sorry, I can't help with that request."}
            return
        for b in resp.content:
            if b.type == "text" and b.text.strip():
                yield {"type": "text", "text": b.text.strip()}
        if resp.stop_reason != "tool_use":
            return
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                out = yield from _call_tool(ctx, b.name, dict(b.input or {}))
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": dumps(out),
                                **({"is_error": True} if isinstance(out, dict) and "error" in out else {})})
        messages.append({"role": "user", "content": results})
    yield {"type": "text", "text": "توقفت بعد عدد كبير من الخطوات. هل يمكنك تضييق طلبك؟" if ctx.lang == "ar"
           else "I stopped after many steps. Could you narrow your request?"}


# ----------------------------------------------------------------- OpenAI
def _run_openai(ctx, message, history, remaining) -> Iterator[dict]:
    from openai import OpenAI

    client = OpenAI(base_url=OPENAI_BASE_URL, timeout=120)      # reads OPENAI_API_KEY
    tools = [{"type": "function", "function": {"name": n, "description": t["description"], "parameters": t["schema"]}}
             for n, t in TOOLS.items()]
    messages = [{"role": "system", "content": _system(ctx.lang)},
                *({"role": h["role"], "content": h["content"]} for h in history if h.get("content")),
                {"role": "user", "content": f"{_context_note(ctx, remaining)}\n\n{message}"}]
    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(model=OPENAI_MODEL, messages=messages, tools=tools, tool_choice="auto")
        msg = resp.choices[0].message
        if msg.refusal:
            yield {"type": "text", "text": "عذراً، لا أستطيع المساعدة في هذا الطلب." if ctx.lang == "ar"
                   else "Sorry, I can't help with that request."}
            return
        calls = [c for c in (msg.tool_calls or []) if c.type == "function"]
        messages.append({
            "role": "assistant", "content": msg.content or "",
            **({"tool_calls": [{"id": c.id, "type": "function",
                                "function": {"name": c.function.name, "arguments": c.function.arguments}}
                               for c in calls]} if calls else {}),
        })
        text = (msg.content or "").strip()
        if text:
            yield {"type": "text", "text": text}
        if not calls:
            return
        for c in calls:
            try:
                args = json.loads(c.function.arguments or "{}")
            except ValueError:
                args = None
            if not isinstance(args, dict):
                out = {"error": "arguments were not valid JSON; call the tool again"}
            else:
                out = yield from _call_tool(ctx, c.function.name, args)
            messages.append({"role": "tool", "tool_call_id": c.id, "content": dumps(out)})
    yield {"type": "text", "text": "توقفت بعد عدد كبير من الخطوات. هل يمكنك تضييق طلبك؟" if ctx.lang == "ar"
           else "I stopped after many steps. Could you narrow your request?"}


# ----------------------------------------------------------------- Ollama
def _run_ollama(ctx, message, history, remaining) -> Iterator[dict]:
    tools = [{"type": "function", "function": {"name": n, "description": t["description"], "parameters": t["schema"]}}
             for n, t in TOOLS.items()]
    messages = [{"role": "system", "content": _system(ctx.lang)},
                *({"role": h["role"], "content": h["content"]} for h in history if h.get("content")),
                {"role": "user", "content": f"{_context_note(ctx, remaining)}\n\n{message}"}]
    with httpx.Client(timeout=180) as http:
        for _ in range(MAX_STEPS):
            r = http.post(f"{OLLAMA_URL}/api/chat", json={
                "model": OLLAMA_MODEL, "messages": messages, "tools": tools, "stream": False,
                "options": {"temperature": 0.2, "num_ctx": 16384}})
            if r.status_code == 404:
                raise RuntimeError(f"Ollama model '{OLLAMA_MODEL}' is not installed. Run: ollama pull {OLLAMA_MODEL}")
            r.raise_for_status()
            msg = r.json()["message"]
            messages.append(msg)
            text = re.sub(r"<think>.*?</think>", "", msg.get("content") or "", flags=re.S).strip()
            calls = msg.get("tool_calls") or []
            if text and not calls:
                yield {"type": "text", "text": text}
            if not calls:
                return
            for call in calls:
                fn = call.get("function", {})
                args = fn.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {}
                out = yield from _call_tool(ctx, fn.get("name", ""), args)
                messages.append({"role": "tool", "tool_name": fn.get("name", ""), "content": dumps(out)})
    yield {"type": "text", "text": "توقفت بعد عدد كبير من الخطوات." if ctx.lang == "ar" else "I stopped after many steps."}


# ------------------------------------------------------------------ rules
def _run_rules(ctx, message, history, remaining) -> Iterator[dict]:
    zakat = "زكا" in message or "zakat" in message.lower()
    waqf = "وقف" in message or "جارية" in message or "waqf" in message.lower() or "endow" in message.lower()
    res = yield from _call_tool(ctx, "search_campaigns",
                                {"query": message, "zakat_only": zakat, "waqf_only": waqf, "limit": 3})
    picks = [c["campaign_id"] for c in res.get("campaigns") or res.get("matches_without_filters") or []][:3]
    ar = ctx.lang == "ar"
    if not picks:
        yield {"type": "text", "text": "لم أجد فرصاً مطابقة. جرّب وصف ما تود دعمه بكلمات أخرى." if ar
               else "I couldn't find matching campaigns. Try describing what you'd like to support differently."}
        return
    yield from _call_tool(ctx, "show_campaigns", {"campaign_ids": picks,
                                                  "heading": "فرص قريبة من طلبك" if ar else "Campaigns close to your request"})
    yield {"type": "text", "text": "هذه أقرب الفرص لطلبك. يمكنك تخصيص جزء من رصيدك الافتراضي لأي منها من البطاقة." if ar
           else "These are the closest matches to your request. You can allocate part of your virtual balance from any card."}


ENGINES = {"openai": _run_openai, "anthropic": _run_anthropic, "ollama": _run_ollama, "rules": _run_rules}


def run(participant_id: str | None, lang: str, wallet: float, remaining: float, message: str,
        history: list[dict] | None = None, engine: str | None = None) -> Iterator[dict]:
    """engine=None uses AGENT_PROVIDER (or the best available)."""
    chosen = engine if engine in ENGINES else pick_engine()
    ctx = ToolContext(participant_id=participant_id, lang=lang, wallet=wallet)
    yield {"type": "start", "engine": chosen, "model": model_for(chosen), "promptVersion": PROMPT_VERSION}
    try:
        said = []
        for ev in ENGINES[chosen](ctx, message, history or [], remaining):
            if ev["type"] == "text":
                ev = {**ev, "text": _polish(ev["text"])}
                said.append(ev["text"])
            yield ev
        block = ground_cards(ctx, "\n".join(said))
        if block:
            yield {"type": "ui", "block": block, "auto": True}
    except Exception as e:
        yield {"type": "error", "message": f"{type(e).__name__}: {e}"[:300]}
        if chosen != "rules":
            yield from _run_rules(ctx, message, history or [], remaining)
    yield {"type": "done", "engine": chosen, "model": model_for(chosen)}
