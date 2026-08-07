from unittest.mock import MagicMock

import pytest

from src.modules.ingestion import chunker as real_chunker
from src.modules.ingestion import embeddings as real_embeddings
from src.modules.ingestion import parser as real_parser
from src.modules.ingestion import repository as real_repository
from src.modules.ingestion.chunker import Chunk
from src.modules.ingestion.embeddings import EmbeddedChunk
from src.modules.ingestion.service import ingest


def _collaborators(text="Some regulation text.", chunks=None, title_exists=False):
    parser = MagicMock(spec=real_parser)
    parser.extract_text.return_value = text

    if chunks is None:
        chunks = [Chunk(text=text, order=0)]
    chunker = MagicMock(spec=real_chunker)
    chunker.chunk_text.return_value = chunks

    embeddings = MagicMock(spec=real_embeddings)
    embeddings.embed_chunk.side_effect = lambda chunk, **kwargs: EmbeddedChunk(
        text=chunk.text, order=chunk.order, embedding=[0.1] * 1024
    )

    repository = MagicMock(spec=real_repository)
    repository.title_exists.return_value = title_exists

    connection_factory = MagicMock(return_value=MagicMock())
    settings_factory = MagicMock(
        return_value=MagicMock(
            aws_region="us-east-1",
            embedding_provider="bedrock",
            ollama_host="http://localhost:11434",
            ollama_embedding_model="mxbai-embed-large",
        )
    )

    return {
        "parser": parser,
        "chunker": chunker,
        "embeddings": embeddings,
        "repository": repository,
        "connection_factory": connection_factory,
        "settings_factory": settings_factory,
    }


def test_ingest_rejects_unsupported_department_before_any_io():
    collaborators = _collaborators()

    with pytest.raises(ValueError):
        ingest("sample.pdf", "Some Title", "engine", **collaborators)

    collaborators["connection_factory"].assert_not_called()
    collaborators["repository"].title_exists.assert_not_called()
    collaborators["parser"].extract_text.assert_not_called()


def test_ingest_rejects_duplicate_title_before_parsing():
    collaborators = _collaborators(title_exists=True)

    with pytest.raises(ValueError):
        ingest("sample.pdf", "Existing Title", "sporting", **collaborators)

    collaborators["repository"].title_exists.assert_called_once()
    collaborators["parser"].extract_text.assert_not_called()
    collaborators["repository"].write_document.assert_not_called()


def test_ingest_propagates_parser_errors_before_any_write():
    collaborators = _collaborators()
    collaborators["parser"].extract_text.side_effect = FileNotFoundError("no such file")

    with pytest.raises(FileNotFoundError):
        ingest("missing.pdf", "Some Title", "sporting", **collaborators)

    collaborators["repository"].write_document.assert_not_called()


def test_ingest_writes_nothing_when_embedding_fails():
    collaborators = _collaborators(chunks=[Chunk(text="a", order=0), Chunk(text="b", order=1)])
    collaborators["embeddings"].embed_chunk.side_effect = RuntimeError("bedrock unavailable")

    with pytest.raises(RuntimeError):
        ingest("sample.pdf", "Some Title", "sporting", **collaborators)

    collaborators["repository"].write_document.assert_not_called()


def test_ingest_happy_path_writes_all_embedded_chunks_together():
    chunks = [Chunk(text="a", order=0), Chunk(text="b", order=1)]
    collaborators = _collaborators(chunks=chunks)

    ingest("sample.pdf", "Some Title", "technical", **collaborators)

    collaborators["repository"].write_document.assert_called_once()
    args, _ = collaborators["repository"].write_document.call_args
    _, written_title, written_department, written_chunks = args
    assert written_title == "Some Title"
    assert written_department == "technical"
    assert len(written_chunks) == 2
    assert all(isinstance(c, EmbeddedChunk) for c in written_chunks)
