from dataclasses import dataclass

CHUNK_WORD_COUNT = 500
CHUNK_OVERLAP_WORDS = 75


@dataclass
class Chunk:
    text: str
    order: int


def chunk_text(text: str) -> list[Chunk]:
    words = text.split()
    if not words:
        return []

    step = CHUNK_WORD_COUNT - CHUNK_OVERLAP_WORDS
    chunks = []
    start = 0
    order = 0

    while start < len(words):
        end = min(start + CHUNK_WORD_COUNT, len(words))
        chunks.append(Chunk(text=" ".join(words[start:end]), order=order))
        order += 1
        if end == len(words):
            break
        start += step

    return chunks
