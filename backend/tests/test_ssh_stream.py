from app.infra.ssh import _clean_stream_text, _is_ui_log_line


def test_clean_stream_splits_carriage_return():
    raw = "line one\rline two\nline three"
    assert _clean_stream_text(raw) == "line one\nline two\nline three"


def test_ui_log_filters_tqdm_bar():
    assert not _is_ui_log_line("embed:  50%|████████          | 1000/2000 [00:10<00:10, 99it/s]")
    assert _is_ui_log_line("[embed] 40000/70757 (56.5%) 70.1 chunks/s ETA 12 min")


def test_ui_log_keeps_pipeline_prefix():
    assert _is_ui_log_line("[pipeline] Products: xdr xsiam")
