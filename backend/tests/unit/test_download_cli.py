from unittest.mock import MagicMock, patch

from src.modules.download.cli import main


def _fake_result(downloaded=None, skipped=None, failed=None):
    return MagicMock(downloaded=downloaded or [], skipped=skipped or [], failed=failed or [])


def test_interactive_mode_counts_before_downloading():
    order = []

    def fake_count(category_id, **kwargs):
        order.append("count")
        return 3

    def fake_download(category_id, output_dir, **kwargs):
        order.append("download")
        return _fake_result()

    with (
        patch("src.modules.download.cli._is_interactive", return_value=True),
        patch("src.modules.download.cli.tqdm") as mock_tqdm,
        patch("src.modules.download.cli.count_documents_in_category", side_effect=fake_count) as mock_count,
        patch("src.modules.download.cli.download_category", side_effect=fake_download),
    ):
        mock_tqdm.write = MagicMock()
        exit_code = main(["--category", "110"])

    assert exit_code == 0
    assert order == ["count", "download"]
    assert "on_page_counted" in mock_count.call_args.kwargs


def test_interactive_mode_creates_a_bounded_bar_with_the_counted_total():
    with (
        patch("src.modules.download.cli._is_interactive", return_value=True),
        patch("src.modules.download.cli.tqdm") as mock_tqdm,
        patch("src.modules.download.cli.count_documents_in_category", return_value=42),
        patch("src.modules.download.cli.download_category", return_value=_fake_result()),
    ):
        mock_tqdm.write = MagicMock()
        main(["--category", "110"])

    # One tqdm() call for the counting phase, one for the bounded download bar.
    bounded_calls = [c for c in mock_tqdm.call_args_list if c.kwargs.get("total") == 42]
    assert len(bounded_calls) == 1


def test_interactive_mode_on_progress_advances_the_bar():
    bar = MagicMock()
    with (
        patch("src.modules.download.cli._is_interactive", return_value=True),
        patch("src.modules.download.cli.tqdm", side_effect=[MagicMock(), bar]) as mock_tqdm,
        patch("src.modules.download.cli.count_documents_in_category", return_value=5),
        patch("src.modules.download.cli.download_category") as mock_download,
    ):
        mock_tqdm.write = MagicMock()

        def fake_download(category_id, output_dir, **kwargs):
            kwargs["on_progress"](3)
            return _fake_result()

        mock_download.side_effect = fake_download
        main(["--category", "110"])

    assert bar.n == 3
    bar.refresh.assert_called()


def test_interactive_mode_on_failure_uses_tqdm_write_not_print(capsys):
    failure = MagicMock(source_url="https://x/a.pdf", title="A", reason="boom")
    with (
        patch("src.modules.download.cli._is_interactive", return_value=True),
        patch("src.modules.download.cli.tqdm") as mock_tqdm,
        patch("src.modules.download.cli.count_documents_in_category", return_value=1),
        patch("src.modules.download.cli.download_category") as mock_download,
    ):
        def fake_download(category_id, output_dir, **kwargs):
            kwargs["on_failure"](failure)
            return _fake_result(failed=[failure])

        mock_download.side_effect = fake_download
        main(["--category", "110"])

    mock_tqdm.write.assert_called_once()
    assert "boom" in mock_tqdm.write.call_args.args[0]


def test_non_interactive_mode_enables_line_buffering(monkeypatch):
    # Verified live: Python fully buffers stdout when redirected, so
    # without this a killed/monitored-mid-run log file can sit empty or
    # stale — reconfigure() must be called before any output is produced.
    reconfigure_calls = []
    monkeypatch.setattr("sys.stdout.reconfigure", lambda **kwargs: reconfigure_calls.append(kwargs))

    with (
        patch("src.modules.download.cli._is_interactive", return_value=False),
        patch("src.modules.download.cli.count_documents_in_category", return_value=1),
        patch("src.modules.download.cli.download_category", return_value=_fake_result()),
    ):
        main(["--category", "110"])

    assert reconfigure_calls == [{"line_buffering": True}]


def test_non_interactive_mode_never_constructs_a_tqdm_object():
    with (
        patch("src.modules.download.cli._is_interactive", return_value=False),
        patch("src.modules.download.cli.tqdm") as mock_tqdm,
        patch("src.modules.download.cli.count_documents_in_category", return_value=3),
        patch("src.modules.download.cli.download_category", return_value=_fake_result()),
    ):
        main(["--category", "110"])

    mock_tqdm.assert_not_called()


def test_non_interactive_mode_prints_one_line_per_page_counted(capsys):
    def fake_count(category_id, **kwargs):
        on_page_counted = kwargs["on_page_counted"]
        on_page_counted(0)
        on_page_counted(1)
        return 5

    with (
        patch("src.modules.download.cli._is_interactive", return_value=False),
        patch("src.modules.download.cli.count_documents_in_category", side_effect=fake_count),
        patch("src.modules.download.cli.download_category", return_value=_fake_result()),
    ):
        main(["--category", "110"])

    out = capsys.readouterr().out
    assert "page 0" in out
    assert "page 1" in out


def test_non_interactive_mode_reports_the_total_once_known(capsys):
    with (
        patch("src.modules.download.cli._is_interactive", return_value=False),
        patch("src.modules.download.cli.count_documents_in_category", return_value=17),
        patch("src.modules.download.cli.download_category", return_value=_fake_result()),
    ):
        main(["--category", "110"])

    assert "17" in capsys.readouterr().out


def test_non_interactive_mode_throttles_progress_lines_to_ten_percent_boundaries(capsys):
    def fake_download(category_id, output_dir, **kwargs):
        on_progress = kwargs["on_progress"]
        for count in range(1, 11):  # total will be 10, so every count is its own 10% boundary
            on_progress(count)
        return _fake_result()

    with (
        patch("src.modules.download.cli._is_interactive", return_value=False),
        patch("src.modules.download.cli.count_documents_in_category", return_value=10),
        patch("src.modules.download.cli.download_category", side_effect=fake_download),
    ):
        main(["--category", "110"])

    out = capsys.readouterr().out
    progress_lines = [line for line in out.splitlines() if line.startswith("Progress:")]
    assert len(progress_lines) == 10


def test_non_interactive_mode_does_not_print_a_progress_line_for_every_document_on_a_large_total(capsys):
    def fake_download(category_id, output_dir, **kwargs):
        on_progress = kwargs["on_progress"]
        for count in range(1, 241):  # total will be 240
            on_progress(count)
        return _fake_result()

    with (
        patch("src.modules.download.cli._is_interactive", return_value=False),
        patch("src.modules.download.cli.count_documents_in_category", return_value=240),
        patch("src.modules.download.cli.download_category", side_effect=fake_download),
    ):
        main(["--category", "110"])

    out = capsys.readouterr().out
    progress_lines = [line for line in out.splitlines() if line.startswith("Progress:")]
    assert len(progress_lines) <= 10


def test_non_interactive_mode_prints_a_failure_line_immediately_regardless_of_throttling(capsys):
    failure = MagicMock(source_url="https://x/a.pdf", title="A", reason="boom")

    def fake_download(category_id, output_dir, **kwargs):
        kwargs["on_failure"](failure)
        return _fake_result(failed=[failure])

    with (
        patch("src.modules.download.cli._is_interactive", return_value=False),
        patch("src.modules.download.cli.count_documents_in_category", return_value=100),
        patch("src.modules.download.cli.download_category", side_effect=fake_download),
    ):
        main(["--category", "110"])

    out = capsys.readouterr().out
    assert "FAILED" in out
    assert "boom" in out
