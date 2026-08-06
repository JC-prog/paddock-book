from pathlib import Path

import pypdf


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    try:
        reader = pypdf.PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except FileNotFoundError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not read PDF file: {file_path}") from exc

    if not text.strip():
        raise ValueError(f"No extractable text found in PDF: {file_path}")

    return text
