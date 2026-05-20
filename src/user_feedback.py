"""User-facing errors: friendly copy, toast, and optional Streamlit dialog."""

from __future__ import annotations

import re
from typing import Tuple

import streamlit as st

_PENDING = "_pending_error_dialog"
_TITLE = "_pending_error_dialog_title"
_SHORT = "_pending_error_dialog_short"
_DETAIL = "_pending_error_dialog_detail"


def friendly_api_message(exc: BaseException) -> Tuple[str, str]:
    """Return (short_markdown, raw_technical_string)."""
    raw = str(exc).strip() or repr(exc)
    low = raw.lower()

    if "429" in raw or "rate_limit" in low or "rate limit" in low:
        m = re.search(r"Please try again in ([0-9hms.\s]+)", raw, re.I)
        wait = m.group(1).strip() if m else None
        m2 = re.search(r"Limit\s+([\d,]+),\s*Used\s+([\d,]+),\s*Requested\s+([\d,]+)", raw, re.I)
        lim = f" (limit {m2.group(1)}, used {m2.group(2)}, this call ~{m2.group(3)} tokens)" if m2 else ""
        msg = (
            "Groq **hit a rate limit** (tokens per day or requests). "
            "This is a provider quota — not a bug in the app."
        )
        if wait:
            msg += f" Try again in about **{wait}**, use **Cursor** mode meanwhile, or upgrade your Groq plan."
        else:
            msg += " Try again later, use **Cursor** mode, or check your Groq billing / tier."
        if lim and "tokens" in low:
            msg += f"\n\n{lim.strip()}"
        return msg, raw

    if "401" in raw or "403" in raw or ("invalid" in low and "api" in low):
        return (
            "The **API key was rejected** or lacks permission. "
            "Confirm **MA_GROQ_KEY** / **GROQ_API_KEY** in the environment where Streamlit runs.",
            raw,
        )

    if "json" in low or "expecting" in low or "decode" in low:
        return (
            "The model response **was not valid JSON**. "
            "Retry the step, shorten the prompt context (e.g. fewer Tavily snippets), or use **Cursor** mode.",
            raw,
        )

    return (
        "The request **did not complete**. See technical details below.",
        raw,
    )


def queue_error_dialog(title: str, exc: BaseException) -> None:
    """Show toast now; render modal dialog on next paint via `maybe_render_error_dialog()`."""
    short, detail = friendly_api_message(exc)
    st.session_state[_PENDING] = True
    st.session_state[_TITLE] = title
    st.session_state[_SHORT] = short
    st.session_state[_DETAIL] = detail
    try:
        plain = re.sub(r"\*+", "", short).strip()
        st.toast(f"{title}: {plain}"[:400], icon="⚠️")
    except Exception:
        pass
    st.error(f"{title} didn’t finish — see the popup for next steps.")


def maybe_render_error_dialog() -> None:
    """Call once per run (e.g. end of `streamlit_app.py`). Opens at most one modal."""
    if not st.session_state.get(_PENDING):
        return

    title = str(st.session_state.get(_TITLE) or "Something went wrong")
    short = str(st.session_state.get(_SHORT) or "")
    detail = str(st.session_state.get(_DETAIL) or "")

    @st.dialog("We couldn’t complete that")
    def _error_dialog() -> None:
        st.markdown(f"#### {title}")
        st.markdown(short)
        if detail:
            with st.expander("Technical details"):
                st.code(detail, language="text")
        if st.button("Dismiss", type="primary", use_container_width=True):
            for k in (_PENDING, _TITLE, _SHORT, _DETAIL):
                st.session_state.pop(k, None)
            st.rerun()

    _error_dialog()


def notify_parse_error(context: str, exc: BaseException) -> None:
    """JSON paste / validation errors: toast + dialog with friendly header."""
    raw = str(exc).strip() or repr(exc)
    st.session_state[_PENDING] = True
    st.session_state[_TITLE] = context
    st.session_state[_SHORT] = (
        "The pasted text **could not be parsed** as the expected JSON. "
        "Check for truncated output, missing braces, or a non-JSON wrapper."
    )
    st.session_state[_DETAIL] = raw
    try:
        st.toast(f"{context}: check JSON shape", icon="⚠️")
    except Exception:
        pass
    st.error(f"{context} — see the popup for the parser message.")
