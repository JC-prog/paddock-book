from src.modules.ingestion.chunker import CHUNK_OVERLAP_WORDS, CHUNK_WORD_COUNT, chunk_text


def test_short_text_produces_a_single_chunk():
    text = "one two three four five"

    chunks = chunk_text(text)

    assert len(chunks) == 1
    assert chunks[0].order == 0
    assert chunks[0].text == text


def test_long_text_splits_into_multiple_chunks_with_sequential_order():
    words = [f"word{i}" for i in range(1200)]
    text = " ".join(words)

    chunks = chunk_text(text)

    assert len(chunks) > 1
    assert [chunk.order for chunk in chunks] == list(range(len(chunks)))


def test_consecutive_chunks_overlap():
    words = [f"word{i}" for i in range(1200)]
    text = " ".join(words)

    chunks = chunk_text(text)

    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    overlap = set(first_words[-CHUNK_OVERLAP_WORDS:]) & set(second_words[:CHUNK_OVERLAP_WORDS])

    assert len(overlap) > 0


def test_chunks_respect_target_word_count():
    words = [f"word{i}" for i in range(1200)]
    text = " ".join(words)

    chunks = chunk_text(text)

    for chunk in chunks[:-1]:
        assert len(chunk.text.split()) == CHUNK_WORD_COUNT


def test_no_content_is_dropped_across_chunk_boundaries():
    words = [f"word{i}" for i in range(1200)]
    text = " ".join(words)

    chunks = chunk_text(text)

    covered_words: set[str] = set()
    for chunk in chunks:
        covered_words.update(chunk.text.split())

    assert covered_words == set(words)


def test_empty_text_produces_no_chunks():
    chunks = chunk_text("")

    assert chunks == []
