from app.llm.strip_thinking import strip_thinking


def test_removes_closed_think_block() -> None:
    assert strip_thinking("<think>reasoning here</think>The answer.") == "The answer."


def test_removes_multiline_block() -> None:
    text = "<think>\nline1\nline2\n</think>\nFinal reply."
    assert strip_thinking(text) == "Final reply."


def test_removes_unclosed_trailing_block() -> None:
    # R1 with exhausted num_predict may never close the tag (Phase 0 failure, doc 19)
    assert strip_thinking("<think>never closed, budget ran out") == ""


def test_plain_text_untouched() -> None:
    assert strip_thinking("Just a normal reply.") == "Just a normal reply."


def test_multiple_blocks() -> None:
    text = "<think>a</think>One. <think>b</think>Two."
    assert strip_thinking(text) == "One. Two."
