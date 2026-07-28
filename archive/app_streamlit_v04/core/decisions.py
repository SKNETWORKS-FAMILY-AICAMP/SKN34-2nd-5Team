from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    import pandas as pd


UNDECIDED_LABEL = "미검토"
KEY_SEPARATOR = "::"

_STORE_PATH = Path(__file__).resolve().parents[1] / ".runtime_state" / "reviewer_decisions.json"


def _load_from_disk() -> dict[str, str]:
    if not _STORE_PATH.exists():
        return {}
    try:
        data = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def _save_to_disk(decisions: dict[str, str]) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(
        json.dumps(decisions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_decisions() -> dict[str, str]:
    """이번 앱 프로세스 동안 공유되는 관리자 판단 저장소.

    새로고침·서버 재시작에도 남도록 로컬 파일에 백업한다. 세션별로
    분리되지 않으므로 여러 브라우저 세션이 동시에 쓰면 같은 판단을
    공유한다 — 단일 운영자 데모 사용을 전제로 한 의도적 단순화다.
    """
    if "reviewer_decisions" not in st.session_state:
        st.session_state["reviewer_decisions"] = _load_from_disk()
    return st.session_state["reviewer_decisions"]


def decision_key(model_version: str, sample_id: str) -> str:
    return f"{model_version}{KEY_SEPARATOR}{sample_id}"


def get_decision(model_version: str, sample_id: str) -> str | None:
    return get_decisions().get(decision_key(model_version, sample_id))


def apply_decision(model_version: str, sample_id: str, decision: str) -> None:
    decisions = get_decisions()
    decisions[decision_key(model_version, sample_id)] = decision
    _save_to_disk(decisions)


def cancel_decision(model_version: str, sample_id: str) -> None:
    decisions = get_decisions()
    key = decision_key(model_version, sample_id)
    if key in decisions:
        del decisions[key]
        _save_to_disk(decisions)


def with_manager_decisions(profiles: "pd.DataFrame") -> "pd.DataFrame":
    """`profiles`에 `manager_decision` 컬럼을 덧붙인 사본을 반환한다.

    판단이 없는 리뷰어는 `UNDECIDED_LABEL`("미검토")로 채운다.
    """
    decisions = get_decisions()
    enriched = profiles.copy()
    keys = (
        enriched["model_version"].astype(str)
        + KEY_SEPARATOR
        + enriched["sample_id"].astype(str)
    )
    enriched["manager_decision"] = keys.map(decisions).fillna(UNDECIDED_LABEL)
    return enriched
