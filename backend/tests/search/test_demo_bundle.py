"""Validate the actual recorded API evidence; corruptions are confined to test copies."""

import json
from copy import deepcopy

import pytest

from scripts.prepare_search_demo import DEFAULT_OUTPUT, validate_bundle


@pytest.fixture
def bundle():
    return json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))


def test_real_saved_demo_has_valid_provenance_and_evidence(bundle):
    before = deepcopy(bundle)
    validate_bundle(bundle)
    assert bundle == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("source", "live_search_api"),
        ("bundle_version", 99),
        ("recorded_at_utc", "2026-11-10T12:00:00"),
        ("recording_method", "synthetic"),
        ("source_revision", ""),
        ("source_sha256", {}),
        ("environment", {}),
        ("working_tree_dirty", None),
    ],
)
def test_invalid_provenance_is_rejected(bundle, field, value):
    bundle[field] = value
    with pytest.raises(ValueError):
        validate_bundle(bundle)


@pytest.mark.parametrize("kind", ["curve", "trials"])
def test_incomplete_recordings_are_rejected(bundle, kind):
    bundle[kind].pop()
    with pytest.raises(ValueError):
        validate_bundle(bundle)


@pytest.mark.parametrize(
    "field,value",
    [
        ("successful_shots", 1025),
        ("classical_observed_queries", 8),
        ("quantum_total_oracle_queries", 99),
        ("success_probability", None),
    ],
)
def test_inconsistent_measurements_are_rejected(bundle, field, value):
    bundle["curve"][2]["metrics"][field] = value
    with pytest.raises(ValueError):
        validate_bundle(bundle)


def test_wrong_trial_seed_is_rejected(bundle):
    bundle["trials"][1]["metadata"]["seed"] = 42
    with pytest.raises(ValueError):
        validate_bundle(bundle)
