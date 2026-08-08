import json
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

MANIFEST_FILENAME = "manifest.json"


@dataclass
class ManifestEntry:
    title: str
    source_url: str
    section: str | None
    issue: str | None
    published_date: str | None
    local_filename: str
    downloaded_at: str


def save_pdf(output_dir: Path, source_url: str, content: bytes) -> str:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = _filename_from_url(source_url)
    (output_dir / filename).write_bytes(content)
    return filename


def record_entry(output_dir: Path, entry: ManifestEntry) -> None:
    manifest = load_manifest(output_dir)
    manifest[entry.source_url] = asdict(entry)
    _write_manifest(output_dir, manifest)


def load_manifest(output_dir: Path) -> dict[str, dict]:
    manifest_path = Path(output_dir) / MANIFEST_FILENAME
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text())


def is_downloaded(manifest: dict[str, dict], source_url: str) -> bool:
    return source_url in manifest


def _write_manifest(output_dir: Path, manifest: dict[str, dict]) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / MANIFEST_FILENAME).write_text(json.dumps(manifest, indent=2))


def _filename_from_url(source_url: str) -> str:
    return Path(urlparse(source_url).path).name
