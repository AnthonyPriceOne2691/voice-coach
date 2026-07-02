from pathlib import Path

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
