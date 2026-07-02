from app.common.sentences import SentenceChunker


def test_single_sentence_completed_by_boundary() -> None:
    chunker = SentenceChunker()
    assert chunker.push("Hello ") == []
    assert chunker.push("world. ") == ["Hello world."]
    assert chunker.flush() is None


def test_multiple_sentences_in_one_token() -> None:
    chunker = SentenceChunker()
    out = chunker.push("First one. Second one? And a tail")
    assert out == ["First one.", "Second one?"]
    assert chunker.flush() == "And a tail"


def test_no_boundary_without_trailing_space() -> None:
    chunker = SentenceChunker()
    assert chunker.push("Version 2.5 is fine") == []
    assert chunker.flush() == "Version 2.5 is fine"


def test_question_and_exclamation_boundaries() -> None:
    chunker = SentenceChunker()
    out = chunker.push("Really?! Yes! Done. ")
    assert out[-1] == "Done."
    assert chunker.flush() is None


def test_quote_after_period() -> None:
    chunker = SentenceChunker()
    out = chunker.push('He said "stop." Then left. ')
    assert out == ['He said "stop."', "Then left."]


def test_flush_resets_buffer() -> None:
    chunker = SentenceChunker()
    chunker.push("partial")
    assert chunker.flush() == "partial"
    assert chunker.flush() is None
