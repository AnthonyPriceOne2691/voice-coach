"""ContractSpec loader: data/contracts/*.yaml -> typed config.

Declarative and not Turing-complete (doc 13): every `check` must be a known name;
unknown checks are rejected at load time, before any runtime evaluation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Checks evaluated by the runtime enforcer on agent text.
RUNTIME_CHECKS = {
    "no_cyrillic",
    "forbid_patterns",
    "max_sentences",
    "max_chars_cumulative",
    "question_or_ack",
    "quoted_question_in_transcript",
}
# Checks owned by other components (orchestrator, pipeline, JSON validator) —
# allowed in YAML as documentation, ignored by the text enforcer.
DECLARATIVE_CHECKS = {
    "session_type_is",
    "knowledge_profile_loaded",
    "interview_exists_with_transcript",
    "interview_transcript_nonempty",
    "mode_persona",
    "orchestrator_nudge",
    "preamble_before_question",
    "ack_present_on_followup",
    "nonempty_after_strip_thinking",
    "json_schema_valid",
    "english_only_fields",
    "scores_int_range",
    "vocabulary_items_complete",
}


class ContractError(ValueError):
    """Malformed contract file."""


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    check: str
    severity: str  # hard | soft
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContractSpec:
    mode: str
    enforcement: str
    rules: list[RuleSpec]
    max_retries: int
    forbidden_patterns: list[str]
    ack_whitelist: list[str]

    def runtime_rules(self) -> list[RuleSpec]:
        return [r for r in self.rules if r.check in RUNTIME_CHECKS]


def _load_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            lines.append(line.lower())
    return lines


def _collect_rules(section: Any, severity: str) -> list[RuleSpec]:
    rules: list[RuleSpec] = []
    for entry in section or []:
        check = entry.get("check")
        rule_id = entry.get("id", check)
        if check is None:
            raise ContractError(f"rule {rule_id!r} has no check")
        if check not in RUNTIME_CHECKS | DECLARATIVE_CHECKS:
            raise ContractError(f"unknown check {check!r} in rule {rule_id!r}")
        params = {k: v for k, v in entry.items() if k not in {"id", "check"}}
        rules.append(RuleSpec(rule_id=rule_id, check=check, severity=severity, params=params))
    return rules


def load_contract(path: Path) -> ContractSpec:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules: list[RuleSpec] = []
    for section in ("invariants", "governance"):
        block = data.get(section) or {}
        rules += _collect_rules(block.get("hard"), "hard")
        rules += _collect_rules(block.get("soft"), "soft")

    contracts_dir = path.parent
    forbidden: list[str] = []
    ack_whitelist: list[str] = []
    for rule in rules:
        patterns_file = rule.params.get("patterns_file")
        if patterns_file and not forbidden:
            forbidden = _load_lines(contracts_dir / str(patterns_file))
        ack_file = rule.params.get("ack_whitelist_file")
        if ack_file and not ack_whitelist:
            ack_whitelist = _load_lines(contracts_dir / str(ack_file))

    recovery = data.get("recovery") or {}
    return ContractSpec(
        mode=str(data.get("mode", path.stem)),
        enforcement=str(data.get("enforcement", "per_sentence")),
        rules=rules,
        max_retries=int(recovery.get("max_retries", 1)),
        forbidden_patterns=forbidden,
        ack_whitelist=ack_whitelist,
    )
