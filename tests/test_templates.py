"""Golden-file regression tests driven by real chat-message templates
under templates/{daily,weekend}/.  The fake OpenAI client is primed
from the matching .expected.json file, so these tests verify the
extract_reports → hydrate → downstream contract, NOT LLM accuracy.
(LLM accuracy is validated manually via scripts/verify_llm_extract.py
against live snapshots.)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import llm_extractor as le


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _discover():
    for sub in ("daily", "weekend"):
        d = TEMPLATES_DIR / sub
        if not d.exists():
            continue
        for p in sorted(d.iterdir()):
            if p.is_file() and not p.name.endswith(".expected.json"):
                exp = p.with_suffix(".expected.json")
                if exp.exists():
                    yield pytest.param(p, exp, id=f"{sub}/{p.name}")


@pytest.mark.parametrize("template_path, expected_path", list(_discover()))
def test_template_extraction(template_path, expected_path,
                             fake_openai, tmp_cache, monkeypatch):
    le._reset_stats()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    content = template_path.read_text(encoding="utf-8")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    reports_only = expected["reports"]
    fake_openai.chat.completions.queue.append({
        "reports": reports_only, "unparseable": False, "reason": None,
    })

    msg = {"content": content,
           "user": {"displayName": "T", "id": "u-t"},
           "createdAt": "2026-04-21T10:00:00Z",
           "id": f"m-{template_path.name}",
           "type": "TEXT"}
    out = le.extract_reports(msg)

    assert len(out) == len(reports_only)
    for actual, exp in zip(out, reports_only):
        for k, v in exp.items():
            assert actual[k] == v, (
                f"{template_path.name}: field {k!r} differs "
                f"(got {actual[k]!r}, want {v!r})"
            )
