"""Test cases — ground-truth query/expected-section pairs for evaluation."""

from __future__ import annotations

from app.models.evaluation import EvalCase

EVAL_CASES: list[EvalCase] = [
    EvalCase(
        id="tc-01",
        query="What is Section 120A IPC criminal conspiracy?",
        expected_section_ids=["ipc-120A-section", "ipc-120B-section"],
        expected_acts=["ipc"],
        query_type="direct",
    ),
    EvalCase(
        id="tc-02",
        query="What is Section 300 IPC murder?",
        expected_section_ids=["ipc-300-section"],
        expected_acts=["ipc"],
        query_type="direct",
    ),
    EvalCase(
        id="tc-03",
        query="What is the difference between culpable homicide and murder?",
        expected_section_ids=["ipc-299-section", "ipc-300-section"],
        expected_acts=["ipc"],
        query_type="comparative",
    ),
    EvalCase(
        id="tc-04",
        query="What is Section 376 IPC?",
        expected_section_ids=["ipc-376-section"],
        expected_acts=["ipc"],
        query_type="direct",
    ),
    EvalCase(
        id="tc-05",
        query="What are the conditions for granting bail in CrPC?",
        expected_section_ids=[
            "crpc-436-section",
            "crpc-437-section",
            "crpc-439-section",
            "crpc-440-section",
            "crpc-441-section",
        ],
        expected_acts=["crpc"],
        query_type="procedural",
    ),
    EvalCase(
        id="tc-06",
        query="What is dowry prohibition under HMA?",
        expected_section_ids=[],
        expected_acts=["hma"],
        query_type="negative",
        should_find_answer=False,
    ),
    EvalCase(
        id="tc-07",
        query="What is Section 379 IPC punishment for theft?",
        expected_section_ids=["ipc-379-section"],
        expected_acts=["ipc"],
        query_type="direct",
    ),
    EvalCase(
        id="tc-08",
        query="What is BNS Section 103?",
        expected_section_ids=["bns-103-section"],
        expected_acts=["bns"],
        query_type="direct",
    ),
    EvalCase(
        id="tc-09",
        query="What is Section 190 CrPC cognizance of offences?",
        expected_section_ids=["crpc-190-section", "crpc-193-section"],
        expected_acts=["crpc"],
        query_type="direct",
    ),
    EvalCase(
        id="tc-10",
        query="What are the rights of an arrested person?",
        expected_section_ids=["crpc-50-section", "crpc-55-section"],
        expected_acts=["crpc"],
        query_type="procedural",
    ),
    EvalCase(
        id="tc-11",
        query="What is adultery under IPC?",
        expected_section_ids=["ipc-497-section", "ipc-494-section", "ipc-498-section"],
        expected_acts=["ipc"],
        query_type="direct",
    ),
    EvalCase(
        id="tc-12",
        query="What is quantum physics?",
        expected_section_ids=[],
        expected_acts=[],
        query_type="negative",
        should_find_answer=False,
    ),
]
