"""Gate 3b — the eight PS query types route to the right node set.

Accuracy is asserted against eval/queries.jsonl so a regression fails CI rather
than being noticed at a demo.

Read the number with its caveat: the weights in classify() were tuned against
this same set, so 100% here is an upper bound, not a generalisation estimate. It
demonstrates the routing layer is wired and measurable; it does not demonstrate
the classifier is good on phrasing it has never seen. The honest fix is the
planner model the stack table specifies, and swapping it in changes classify()
alone.
"""

import json
import pathlib

import pytest

from dhruva.graph.build import INTENT_NODES, classify, score_intents
from dhruva.graph.state import Intent

EVAL = pathlib.Path(__file__).resolve().parents[2] / "eval" / "queries.jsonl"
TARGET = 0.92


def _load() -> list[dict]:
    rows = []
    for line in EVAL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not row.get("_meta"):
            rows.append(row)
    return rows


CASES = _load()


class TestEvalSet:
    def test_the_eval_set_exists_and_is_not_thin(self):
        assert len(CASES) >= 50

    def test_all_eight_question_types_are_represented(self):
        covered = {c["expected_intent"] for c in CASES}
        assert covered == {i.value for i in Intent}

    def test_the_set_is_not_only_english(self):
        """A router that only works in English fails the users this is built for."""
        assert {c["language"] for c in CASES} >= {"en", "ta", "hi"}

    def test_every_case_declares_an_expected_node_set(self):
        for c in CASES:
            assert c["expected_nodes"], c["id"]

    def test_answer_ground_truth_is_absent_and_says_so(self):
        """IMPLEMENTATION.md wants answers sourced from INCOIS or IMD bulletins.
        Those are not in hand, so the field is null rather than invented — an
        unsourced expectation is worthless."""
        assert all(c["expected_answer"] is None for c in CASES)


class TestGate3b:
    def test_intent_routing_meets_the_target(self):
        hits = [c for c in CASES if classify(c["query"]).value == c["expected_intent"]]
        accuracy = len(hits) / len(CASES)
        misses = [
            f"{c['id']}: {c['query'][:40]!r} expected {c['expected_intent']} "
            f"got {classify(c['query']).value}"
            for c in CASES
            if classify(c["query"]).value != c["expected_intent"]
        ]
        assert accuracy >= TARGET, f"{accuracy:.1%} < {TARGET:.0%}\n" + "\n".join(misses)

    def test_each_intent_routes_to_the_right_node_set(self):
        for c in CASES:
            expected = c["expected_nodes"]
            got = ["discovery", *INTENT_NODES[classify(c["query"])]]
            assert got == expected, f"{c['id']} {c['query'][:40]!r}: {got} != {expected}"


class TestRoutingShape:
    def test_node_sets_differ_between_intents(self):
        """If every intent fetched from every node this would not be routing, it
        would be fetching everything and calling it a plan."""
        sets = {tuple(v) for v in INTENT_NODES.values()}
        assert len(sets) > 1

    def test_discovery_runs_for_every_intent(self):
        for intent in Intent:
            assert intent in INTENT_NODES

    def test_an_unrecognised_query_falls_back_rather_than_raising(self):
        assert classify("zzzz qqqq") is Intent.CONDITIONS

    def test_an_empty_query_falls_back(self):
        assert classify("") is Intent.CONDITIONS

    @pytest.mark.parametrize(
        ("query", "intent"),
        [
            ("Why did you say caution?", Intent.EXPLAIN),
            ("Why has the catch fallen here?", Intent.DECLINE_ATTRIBUTION),
        ],
    )
    def test_the_two_why_intents_are_separated_by_what_is_being_asked_about(self, query, intent):
        """Both start with "why". One asks about the system's own answer, the
        other about the ocean, and conflating them sends the wrong nodes."""
        assert classify(query) is intent

    def test_a_safety_question_mentioning_fishing_is_still_a_safety_question(self):
        """ "Is it safe to go fishing today?" carries both signals. Ordered
        first-match answers this by accident of list order; scoring answers it by
        weight."""
        assert classify("Is it safe to go fishing today?") is Intent.GO_NO_GO

    def test_scores_are_exposed_for_inspection(self):
        scores = score_intents("Is there a cyclone warning?")
        assert scores.get(Intent.HAZARD, 0) > 0
