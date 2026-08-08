import json

from src.modules.download.repository import (
    ManifestEntry,
    is_downloaded,
    load_manifest,
    record_entry,
    save_pdf,
)


def _entry(source_url="https://www.fia.com/system/files/documents/foo.pdf", **overrides):
    defaults = dict(
        title="FIA 2026 F1 Regulations - Section B [Sporting] - Iss 08 - 2026-08-05",
        source_url=source_url,
        section="Section B [Sporting]",
        issue="08",
        published_date="2026-08-05",
        local_filename="foo.pdf",
        downloaded_at="2026-08-08T14:32:01Z",
    )
    defaults.update(overrides)
    return ManifestEntry(**defaults)


def test_save_pdf_writes_the_content_and_returns_a_filename_derived_from_the_url(tmp_path):
    filename = save_pdf(tmp_path, "https://www.fia.com/system/files/documents/foo.pdf", b"%PDF-1.4 fake content")

    assert filename == "foo.pdf"
    assert (tmp_path / "foo.pdf").read_bytes() == b"%PDF-1.4 fake content"


def test_save_pdf_creates_the_output_directory_if_it_does_not_exist(tmp_path):
    output_dir = tmp_path / "nested" / "regulations"

    save_pdf(output_dir, "https://www.fia.com/system/files/documents/bar.pdf", b"content")

    assert (output_dir / "bar.pdf").exists()


def test_record_entry_creates_manifest_json_when_none_exists(tmp_path):
    entry = _entry()

    record_entry(tmp_path, entry)

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest[entry.source_url]["title"] == entry.title
    assert manifest[entry.source_url]["local_filename"] == "foo.pdf"


def test_record_entry_appends_to_an_existing_manifest_without_losing_prior_entries(tmp_path):
    first = _entry(source_url="https://www.fia.com/.../a.pdf", local_filename="a.pdf")
    second = _entry(source_url="https://www.fia.com/.../b.pdf", local_filename="b.pdf")

    record_entry(tmp_path, first)
    record_entry(tmp_path, second)

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert set(manifest.keys()) == {first.source_url, second.source_url}


def test_load_manifest_round_trips_a_recorded_entry(tmp_path):
    entry = _entry()
    record_entry(tmp_path, entry)

    manifest = load_manifest(tmp_path)

    assert manifest[entry.source_url]["section"] == entry.section
    assert manifest[entry.source_url]["issue"] == entry.issue
    assert manifest[entry.source_url]["published_date"] == entry.published_date
    assert manifest[entry.source_url]["downloaded_at"] == entry.downloaded_at


def test_load_manifest_returns_empty_dict_when_no_manifest_file_exists(tmp_path):
    assert load_manifest(tmp_path) == {}


def test_is_downloaded_is_true_for_a_url_present_in_the_manifest(tmp_path):
    entry = _entry()
    record_entry(tmp_path, entry)
    manifest = load_manifest(tmp_path)

    assert is_downloaded(manifest, entry.source_url) is True


def test_is_downloaded_is_false_for_a_url_not_present_in_the_manifest(tmp_path):
    manifest = load_manifest(tmp_path)

    assert is_downloaded(manifest, "https://www.fia.com/never-downloaded.pdf") is False
