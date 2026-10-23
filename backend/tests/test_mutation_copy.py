"""Копия пакета у мутационного гейта обязана ИМПОРТИРОВАТЬСЯ (M5).

mutmut 3.7 ставит трамплин под исходным именем метода, а копию оригинала и мутанты
кладёт следом с той же подписью. Аннотация метода вычисляется в теле класса в
момент определения, и имя, совпавшее с уже объявленным методом, указывает на
функцию: `def list(...) -> list[VocabularyEntry]` в `VocabularyRepository` давал
под копией `TypeError: 'function' object is not subscriptable`. Сьют не собирался,
и гейт не просудил ничего — на каждом PR с python (замер 2026-10-23).

`from __future__ import annotations` откладывает вычисление аннотаций и закрывает
класс целиком; без него такой метод — находка этого теста.
"""

import ast

from app.config import REPO_ROOT

APP = REPO_ROOT / "backend" / "app"


def _postponed(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )


def _annotation_names(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    args = fn.args
    params = [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg]
    annotations = [p.annotation for p in params if p is not None] + [fn.returns]
    return {
        node.id
        for annotation in annotations
        if annotation is not None
        for node in ast.walk(annotation)
        if isinstance(node, ast.Name)
    }


def _shadowed(tree: ast.Module) -> list[str]:
    """Методы, чьи аннотации называют уже объявленный (или свой же) метод класса."""
    found: list[str] = []
    for cls in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
        bound: set[str] = set()
        for item in cls.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                bound.add(item.name)
                found += [
                    f"{cls.name}.{item.name} → {name}"
                    for name in sorted(_annotation_names(item) & bound)
                ]
    return found


def test_method_names_do_not_shadow_class_scope_annotations() -> None:
    """M5: ни один метод не прячет имя, которое аннотация вычисляет в теле класса."""
    offenders = []
    for path in sorted(APP.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if not _postponed(tree):
            rel = path.relative_to(REPO_ROOT).as_posix()
            offenders += [f"{rel}: {hit}" for hit in _shadowed(tree)]
    assert offenders == [], (
        "под копией mutmut эти аннотации укажут на трамплин метода, а не на тип, и "
        "сьют не соберётся — гейт не просудит ничего. Добавь в модуль "
        f"`from __future__ import annotations` или переименуй метод: {offenders}"
    )


def test_the_guard_finds_the_case_it_was_written_for() -> None:
    """M5: сторож узнаёт ровно ту форму, что ломала гейт, и молчит при отложенных аннотациях."""
    source = "class Repo:\n    async def list(self) -> list[int]:\n        return []\n"
    assert _shadowed(ast.parse(source)) == ["Repo.list → list"]
    assert _postponed(ast.parse("from __future__ import annotations\n" + source))
    assert not _postponed(ast.parse(source))
