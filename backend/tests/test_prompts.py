from pathlib import Path

from app.contracts.enforcer import ContractEnforcer, TurnContext
from app.contracts.spec import load_contract
from app.knowledge.prompts import PromptLibrary


def _make_dirs(tmp_path: Path) -> tuple[Path, Path]:
    prompts = tmp_path / "prompts"
    (prompts / "templates").mkdir(parents=True)
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    return prompts, knowledge


def test_profile_injected_into_system_prompt(tmp_path: Path) -> None:
    prompts, knowledge = _make_dirs(tmp_path)
    (prompts / "interviewer_system.txt").write_text("PROFILE:\n{{profile_condensed}}\nEND")
    (knowledge / "profile_condensed.md").write_text("Anton, builder of things")

    library = PromptLibrary(prompts, knowledge)
    system = library.interviewer_system()
    assert "Anton, builder of things" in system
    assert "{{profile_condensed}}" not in system


def test_missing_profile_uses_placeholder_text(tmp_path: Path) -> None:
    prompts, knowledge = _make_dirs(tmp_path)
    (prompts / "interviewer_system.txt").write_text("X {{profile_condensed}} Y")

    system = PromptLibrary(prompts, knowledge).interviewer_system()
    assert "(no candidate profile available)" in system


def test_template_loading(tmp_path: Path) -> None:
    prompts, knowledge = _make_dirs(tmp_path)
    (prompts / "templates" / "interview_intro.txt").write_text("Hi there.\n")

    assert PromptLibrary(prompts, knowledge).template("interview_intro") == "Hi there."


def test_real_repo_prompts_load() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    library = PromptLibrary(repo_root / "data" / "prompts", repo_root / "data" / "knowledge")
    system = library.interviewer_system()
    assert "{{profile_condensed}}" not in system
    assert "AI Automation Engineer" in system  # profile really injected
    assert library.template("interview_intro")


def test_pace_templates_exist_and_survive_the_contract() -> None:
    """Реплика подтверждения обязана быть произносимой (L24).

    Она идёт мимо `TurnRunner`, поэтому енфорсер её не режет, — но если завтра
    путь изменится, а слова окажутся запрещёнными, Генри просто ОНЕМЕЕТ на
    просьбе о темпе, и ни один другой тест этого не покажет.
    """
    repo_root = Path(__file__).resolve().parents[2]
    contracts_dir = repo_root / "data" / "contracts"
    library = PromptLibrary(repo_root / "data" / "prompts", repo_root / "data" / "knowledge")
    spec = load_contract(contracts_dir / "interview.contract.yaml")
    enforcer = ContractEnforcer(spec)

    for name in (
        "pace_slower",
        "pace_faster",
        "pace_slowest",
        "pace_fastest",
        # Ответы на просьбы к самому Генри — тот же путь мимо `TurnRunner`.
        "meta_score",
        "meta_language",
        "meta_where_to_start",
    ):
        line = library.template(name)
        assert line, f"{name} пуст"
        turn = enforcer.start_turn(TurnContext(state="CORE_QUEST"))
        assert turn.feed(line) is None, f"{name} режется контрактом: {line!r}"

    # Красная сторона (L25): если бы реплика содержала запрещённое, сторож обязан
    # покраснеть. Без этой проверки он был бы зелёным при любом контракте.
    red = enforcer.start_turn(TurnContext(state="CORE_QUEST"))
    assert red.feed("Sure, slowing down. I'd rate that answer four out of 5.") is not None
