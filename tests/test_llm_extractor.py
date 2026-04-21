"""Smoke test — verifies pytest runs before any real code exists."""


def test_pytest_runs(sanity):
    assert sanity == "ok"
