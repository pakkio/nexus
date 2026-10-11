"""Tests for provider order/fallback and Jev shadow sampling in typesafe_router."""
import json

import pytest

import typesafe_router as T

Q = {"intent": {"type": "choice", "instructions": "x", "criteria": {"go": "g", "talk": "t"}},
     "trait_a": {"type": "score", "instructions": "x", "criteria": ["lo", "hi"]}}


class FakeResp:
    def __init__(self, status, answers=None):
        self.status_code, self._a, self.text = status, answers, "err"

    def json(self):
        return {"answers": self._a, "model": "m", "usage": {}}


def _ans(choice, conf, score=1.0):
    return {"intent": {"type": "choice", "choice": choice, "confidence": conf}, "trait_a": {"type": "score", "score": score}}


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.setenv("TYPESAFE_API_KEY", "ts-key")
    monkeypatch.delenv("TYPESAFE_PROVIDER_ORDER", raising=False)
    monkeypatch.setenv("TYPESAFE_SHADOW_RATE", "0")
    monkeypatch.setenv("TYPESAFE_SHADOW_LOG", str(tmp_path / "shadow.jsonl"))
    T._breaker.clear()


def _post(routes, calls):
    def post(url, **kw):
        calls.append((url, kw["json"]["model"]))
        return routes[url]()
    return post


def test_pplx_is_first_and_uses_openrouter_model(monkeypatch):
    calls = []
    routes = {T.PPLX_ENDPOINT: lambda: FakeResp(200, _ans("go", 0.9)),
              T.ENDPOINT: lambda: FakeResp(200, _ans("talk", 0.9))}
    monkeypatch.setattr("requests.post", _post(routes, calls))
    answers, meta = T.system_one({"s": 1}, Q)
    assert answers["intent"]["choice"] == "go" and meta["provider"] == "pplx"
    assert calls == [(T.PPLX_ENDPOINT, T.PPLX_MODEL_DEFAULT)]


@pytest.mark.parametrize("failure", [lambda: FakeResp(429), lambda: FakeResp(500), lambda: (_ for _ in ()).throw(TimeoutError("t"))])
def test_falls_back_to_jev_on_error(monkeypatch, failure):
    calls = []
    routes = {T.PPLX_ENDPOINT: failure, T.ENDPOINT: lambda: FakeResp(200, _ans("talk", 0.8))}
    monkeypatch.setattr("requests.post", _post(routes, calls))
    answers, meta = T.system_one({"s": 1}, Q)
    assert answers["intent"]["choice"] == "talk" and meta["provider"] == "typesafe"
    assert [c[0] for c in calls] == [T.PPLX_ENDPOINT, T.ENDPOINT]


def test_provider_order_env_restores_jev_first(monkeypatch):
    monkeypatch.setenv("TYPESAFE_PROVIDER_ORDER", "jev,pplx")
    calls = []
    routes = {T.ENDPOINT: lambda: FakeResp(200, _ans("talk", 0.8))}
    monkeypatch.setattr("requests.post", _post(routes, calls))
    T.system_one({"s": 1}, Q)
    assert [c[0] for c in calls] == [T.ENDPOINT]


def test_shadow_logs_paired_answers_and_summary(monkeypatch, tmp_path):
    routes = {T.ENDPOINT: lambda: FakeResp(200, _ans("go", 0.5, score=2.0))}
    monkeypatch.setattr("requests.post", _post(routes, []))
    assert T._shadow_compare("pplx", {"player_input": "vado"}, Q, _ans("go", 0.9, score=1.0), {"elapsed_ms": 300})
    rec = json.loads(open(tmp_path / "shadow.jsonl").read())
    assert rec["answers"]["intent"] == {"pplx": {"choice": "go", "confidence": 0.9},
                                        "jev": {"choice": "go", "confidence": 0.5}}
    summary = T.summarize_shadow_log()
    assert summary["intent"]["agree_rate"] == 1.0
    assert summary["intent"]["gate_split"] == 1          # pplx clears 0.6, Jev does not
    assert summary["trait_a"]["mean_score_gap"] == 1.0


def test_shadow_not_sampled_for_jev_or_when_disabled(monkeypatch):
    started = []
    monkeypatch.setattr("threading.Thread", lambda **kw: type("Th", (), {"start": lambda self: started.append(kw)})())
    monkeypatch.setenv("TYPESAFE_SHADOW_RATE", "1")
    T._maybe_shadow("jev", {}, Q, _ans("go", 0.9), {})
    assert not started
    T._maybe_shadow("pplx", {}, Q, _ans("go", 0.9), {})
    assert len(started) == 1
    started.clear()
    monkeypatch.setenv("TYPESAFE_SHADOW_RATE", "0")
    T._maybe_shadow("pplx", {}, Q, _ans("go", 0.9), {})
    assert not started


def test_shadow_failure_is_silent(monkeypatch):
    monkeypatch.setattr("requests.post", _post({T.ENDPOINT: lambda: FakeResp(500)}, []))
    assert T._shadow_compare("pplx", {}, Q, _ans("go", 0.9), {}) is False
