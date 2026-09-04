"""Render an AgentDojo per-task ``TaskResults`` payload (the dict written to
``<injection_task>.json``) as a standalone HTML trace, saved next to the JSON.

The page shows the message transcript (system / user / assistant + tool_calls /
tool results) and, when Progent is the defense, its components: the generated
allow-list policy, the per-round policy-update trace, and tool calls the policy
blocked. Purely mechanical -- it renders exactly what is in the payload.
"""

from __future__ import annotations

import html
import json
from typing import Any

# Substrings that mark a tool result as a Progent (or other) policy block.
_BLOCK_MARKERS = ("is not allowed", "ValidationError", "denied by the security policy")


def _text(content: Any) -> str:
    """Flatten AgentDojo content (list of {type, content} blocks, str, or None) to plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("content", "")))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def _esc(s: Any) -> str:
    return html.escape(str(s), quote=False)


def _fmt_args(args: Any) -> str:
    try:
        return json.dumps(args, ensure_ascii=False, default=str)
    except Exception:
        return str(args)


def _badge(ok: bool, label_true: str, label_false: str) -> str:
    cls = "ok" if ok else "no"
    return f'<span class="tag {cls}">{label_true if ok else label_false}</span>'


def _policy_card(payload: dict) -> str:
    policy = payload.get("security_policy")
    trace = payload.get("policy_trace")
    if not policy and not trace:
        return ""

    rows = []
    for entry in policy or []:
        name = _esc(entry.get("name", "?"))
        args = entry.get("args") or {}
        arg_names = ", ".join(args.keys()) if isinstance(args, dict) else ""
        sig = f"{name}({_esc(arg_names)})" if arg_names else name
        rows.append(f'<div><span class="tag ok">allow</span>{sig}</div>')
    allow_grid = f'<div class="tools-grid mono">{"".join(rows)}</div>' if rows else ""

    trace_note = ""
    if trace:
        steps = list(trace)
        gen = sum(1 for s in steps if s.get("step") == "generate")
        upd = [s for s in steps if s.get("step") == "update"]
        expanded = sum(1 for s in upd if s.get("expanded"))
        trace_note = (
            f'<div class="box"><div class="box-label">POLICY TRACE</div>'
            f'<div class="mono" style="font-size:11px;color:#4c1d95;">'
            f'{gen} generate · {len(upd)} update step(s) · {expanded} expanded '
            f'(policy {"grew" if expanded else "never grew"})</div></div>'
        )

    return (
        '<div class="msg polcard"><span class="role">Policy</span>'
        '<div>Progent allow-list generated from the (trusted) user query; every other tool call is '
        'denied. Args in parentheses are the constrained parameters.</div>'
        f'<div class="box"><div class="box-label">ALLOW-LIST ({len(policy or [])} tools)</div>{allow_grid}</div>'
        f'{trace_note}</div>'
    )


def _tool_calls_html(tool_calls: list) -> str:
    if not tool_calls:
        return ""
    chips = []
    for tc in tool_calls:
        fn = tc.get("function", "?")
        args = tc.get("args", {})
        chips.append(f"→ {_esc(fn)}({_esc(_fmt_args(args))})")
    return f'<code class="call">{chr(10).join(chips)}</code>'


def _message_html(m: dict) -> str:
    role = m.get("role", "")
    text = _text(m.get("content"))

    if role == "system":
        return f'<div class="msg sys"><span class="role">System</span><div>{_esc(text)}</div></div>'
    if role == "user":
        return f'<div class="msg usr"><span class="role">User</span><div>{_esc(text)}</div></div>'
    if role == "assistant":
        body = f"<div>{_esc(text)}</div>" if text.strip() else ""
        calls = _tool_calls_html(m.get("tool_calls") or [])
        return f'<div class="msg ast"><span class="role">Assistant</span>{body}{calls}</div>'
    if role == "tool":
        error = m.get("error")
        blocked = bool(error) or any(mk in text for mk in _BLOCK_MARKERS)
        call = m.get("tool_call") or {}
        fn = call.get("function", "")
        header = f'<div class="mono" style="font-size:11px;color:#78716c;">{_esc(fn)}</div>' if fn else ""
        if blocked:
            shown = _esc(error) if error else _esc(text)
            return (
                '<div class="msg blocked"><span class="role">Blocked</span>'
                f'{header}<code class="errbox">✗ {shown}</code></div>'
            )
        return (
            '<div class="msg tool"><span class="role">Tool</span>'
            f'{header}<code class="result">{_esc(text)}</code></div>'
        )
    # fallback
    return f'<div class="msg sys"><span class="role">{_esc(role)}</span><div>{_esc(text)}</div></div>'


_STYLE = """
  :root { --sys:#64748b; --usr:#2563eb; --ast:#16a34a; --tool:#d97706; --pol:#7c3aed; --blk:#b91c1c; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:"Helvetica Neue", Arial, sans-serif; background:#fff; display:flex; justify-content:center; padding:24px; }
  .figure { width:940px; max-width:100%; }
  .title { font-size:15px; font-weight:700; color:#111; margin-bottom:4px; }
  .title span { font-weight:400; color:#666; font-size:13px; }
  .subnote { font-size:11.5px; color:#94a3b8; margin-bottom:12px; }
  .msg { border:1.5px solid; border-radius:8px; padding:10px 14px; margin-bottom:10px; font-size:12.5px; line-height:1.45; color:#1f2937; position:relative; }
  .role { display:inline-block; font-size:10.5px; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; color:#fff; border-radius:4px; padding:2px 8px; margin-bottom:6px; }
  .sys { border-color:var(--sys); background:#f8fafc; } .sys .role { background:var(--sys); }
  .usr { border-color:var(--usr); background:#eff6ff; } .usr .role { background:var(--usr); }
  .ast { border-color:var(--ast); background:#f0fdf4; } .ast .role { background:var(--ast); }
  .tool { border-color:var(--tool); background:#fffbeb; margin-left:32px; } .tool .role { background:var(--tool); }
  .blocked { border-color:var(--blk); background:#fef2f2; margin-left:32px; } .blocked .role { background:var(--blk); }
  .polcard { border-color:var(--pol); background:#f5f3ff; } .polcard .role { background:var(--pol); }
  code, .mono { font-family:"SF Mono", Menlo, Consolas, monospace; font-size:11.5px; }
  .call { background:#dcfce7; border:1px solid #86efac; border-radius:6px; padding:6px 10px; margin-top:6px; display:block; white-space:pre-wrap; overflow-x:auto; }
  .result { background:#fef3c7; border:1px solid #fcd34d; border-radius:6px; padding:6px 10px; margin-top:4px; display:block; white-space:pre-wrap; overflow-x:auto; }
  .errbox { background:#fee2e2; border:1px solid #fca5a5; border-radius:6px; padding:6px 10px; margin-top:4px; display:block; white-space:pre-wrap; overflow-x:auto; color:#7f1d1d; }
  .box { margin-top:8px; border-top:1px dashed #c4b5fd; padding-top:8px; }
  .box-label { font-size:10.5px; font-weight:700; color:var(--pol); letter-spacing:0.06em; margin-bottom:4px; }
  .tools-grid { display:grid; grid-template-columns:1fr 1fr; gap:2px 18px; } .tools-grid div { font-size:11px; color:#334155; }
  .tag { display:inline-block; font-size:9.5px; font-weight:700; color:#fff; border-radius:3px; padding:0 4px; margin-right:5px; min-width:38px; text-align:center; }
  .ok { background:#1E8E5A; } .no { background:var(--blk); }
"""


def render_trace_html(payload: dict) -> str:
    """Render a per-task payload dict (as written to the JSON) to a standalone HTML string."""
    suite = payload.get("suite_name", "?")
    user_task = payload.get("user_task_id", "?")
    inj = payload.get("injection_task_id")
    attack = payload.get("attack_type") or "none"
    pipeline = payload.get("pipeline_name", "?")
    utility = payload.get("utility")
    security = payload.get("security")
    duration = payload.get("duration")
    error = payload.get("error")

    dur_str = f"{duration:.2f} s" if isinstance(duration, (int, float)) else "—"
    util_badge = "utility ✓" if utility else "utility ✗"
    sec_badge = "security ✓" if security else "security ✗"

    msgs = payload.get("messages") or []
    n_calls = sum(len(m.get("tool_calls") or []) for m in msgs if m.get("role") == "assistant")

    header = (
        f'<div class="title">Execution Trace <span>— AgentDojo · {_esc(suite)} · {_esc(user_task)} · '
        f'attack: {_esc(attack)} · {_esc(pipeline)} · {util_badge} {sec_badge}</span></div>'
        f'<div class="subnote">injection_task: {_esc(inj if inj is not None else "none")} · '
        f'{n_calls} tool call(s) · {dur_str}</div>'
    )

    body = [_policy_card(payload)]
    body += [_message_html(m) for m in msgs]
    if error:
        body.append(f'<div class="msg blocked"><span class="role">Error</span><code class="errbox">{_esc(error)}</code></div>')

    return (
        "<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"UTF-8\">"
        f"<title>Trace — {_esc(suite)} / {_esc(user_task)} / {_esc(inj or 'none')}</title>"
        f"<style>{_STYLE}</style></head><body><div class=\"figure\">"
        f"{header}{''.join(body)}"
        "</div></body></html>\n"
    )
