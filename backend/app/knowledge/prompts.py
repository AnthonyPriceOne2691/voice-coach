"""Load prompt files from data/prompts/ and inject condensed profile (docs 05, 16)."""

from pathlib import Path

PROFILE_PLACEHOLDER = "{{profile_condensed}}"


class PromptLibrary:
    """Prompts live in data/, not in code (DRY + versioning, doc 18)."""

    def __init__(self, prompts_dir: Path, knowledge_dir: Path) -> None:
        self._prompts_dir = prompts_dir
        self._knowledge_dir = knowledge_dir

    def interviewer_system(self) -> str:
        system = (self._prompts_dir / "interviewer_system.txt").read_text(encoding="utf-8")
        profile_path = self._knowledge_dir / "profile_condensed.md"
        profile = (
            profile_path.read_text(encoding="utf-8")
            if profile_path.exists()
            else "(no candidate profile available)"
        )
        return system.replace(PROFILE_PLACEHOLDER, profile)

    def template(self, name: str) -> str:
        path = self._prompts_dir / "templates" / f"{name}.txt"
        return path.read_text(encoding="utf-8").strip()
