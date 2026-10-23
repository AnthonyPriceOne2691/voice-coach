"""Load prompt files from data/prompts/ and inject condensed profile (docs 05, 16)."""

from pathlib import Path

PROFILE_PLACEHOLDER = "{{profile_condensed}}"
SEGMENTS_PLACEHOLDER = "{{interview_qa_segments}}"
UTTERANCE_PLACEHOLDER = "{{utterance}}"


class PromptLibrary:
    """Prompts live in data/, not in code (DRY + versioning, doc 18)."""

    def __init__(self, prompts_dir: Path, knowledge_dir: Path) -> None:
        self._prompts_dir = prompts_dir
        self._knowledge_dir = knowledge_dir

    def interviewer_system(self) -> str:
        system = (self._prompts_dir / "interviewer_system.txt").read_text(encoding="utf-8")
        return system.replace(PROFILE_PLACEHOLDER, self._profile())

    def talk_system(self) -> str:
        system = (self._prompts_dir / "talk_system.txt").read_text(encoding="utf-8")
        return system.replace(PROFILE_PLACEHOLDER, self._profile())

    def review_system(self, qa_segments: str) -> str:
        system = (self._prompts_dir / "review_system.txt").read_text(encoding="utf-8")
        return system.replace(SEGMENTS_PLACEHOLDER, qa_segments).replace(
            PROFILE_PLACEHOLDER, self._profile()
        )

    def language_check(self, utterance: str) -> str:
        """Просьба о проверке речи — дописывается В КОНЕЦ разговора (D3a.2).

        Реплика подставляется дословно: модель обязана цитировать фрагмент из неё,
        и код потом сверяет цитату с распознанным текстом.
        """
        request = (self._prompts_dir / "language_check.txt").read_text(encoding="utf-8")
        return request.replace(UTTERANCE_PLACEHOLDER, utterance).strip()

    def system(self, name: str) -> str:
        """Raw system prompt file (summary passes inject their own context)."""
        return (self._prompts_dir / f"{name}.txt").read_text(encoding="utf-8")

    def template(self, name: str) -> str:
        path = self._prompts_dir / "templates" / f"{name}.txt"
        return path.read_text(encoding="utf-8").strip()

    def _profile(self) -> str:
        profile_path = self._knowledge_dir / "profile_condensed.md"
        return (
            profile_path.read_text(encoding="utf-8")
            if profile_path.exists()
            else "(no candidate profile available)"
        )
