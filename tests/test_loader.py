import io

import pandas as pd
import pytest

from src.data.loader import UploadError, read_upload, validate_upload


def excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return buffer.getvalue()


@pytest.mark.parametrize("name", ["data.xls", "data.xlsm", "script.py", "data.txt", "noextension"])
def test_unsupported_extensions_are_rejected(name):
    with pytest.raises(UploadError, match="not supported"):
        validate_upload(name, b"a,b\n1,2\n")


def test_empty_file_is_rejected():
    with pytest.raises(UploadError, match="empty"):
        validate_upload("data.csv", b"")


def test_size_limit():
    with pytest.raises(UploadError, match="limit"):
        validate_upload("data.csv", b"a,b\n" + b"1,2\n" * 1000, max_mb=0.001)


def test_fake_excel_is_rejected():
    with pytest.raises(UploadError, match="not a valid Excel"):
        validate_upload("data.xlsx", b"just some text")


def test_binary_csv_is_rejected():
    with pytest.raises(UploadError, match="binary"):
        validate_upload("data.csv", b"a,b\n\x00\x01\x02")


def test_reads_comma_csv():
    loaded = read_upload("data.csv", b"Invoice,Price\n1,2.5\n2,3.0\n")
    assert loaded.data.shape == (2, 2)
    assert loaded.data["Price"].sum() == pytest.approx(5.5)


def test_reads_semicolon_csv_with_windows_encoding():
    content = "Product;Price\nMug £;2,5\nPlate;3\n".encode("cp1252")
    loaded = read_upload("data.csv", content)
    assert list(loaded.data.columns) == ["Product", "Price"]
    assert loaded.data.loc[0, "Product"] == "Mug £"
    assert "cp1252" in loaded.notes[0]


def test_malformed_csv_gives_friendly_error():
    with pytest.raises(UploadError, match="could not be read"):
        read_upload("data.csv", b"a,b\n1,2\n1,2,3,4\n")


def test_single_column_file_is_rejected():
    with pytest.raises(UploadError, match="fewer than two columns"):
        read_upload("data.csv", b"only\n1\n2\n")


def test_row_limit():
    with pytest.raises(UploadError, match="limit"):
        read_upload("data.csv", b"a,b\n1,2\n3,4\n5,6\n", max_rows=2)


def test_reads_first_excel_sheet_by_default():
    content = excel_bytes({"Jan": pd.DataFrame({"a": [1], "b": [2]}),
                           "Feb": pd.DataFrame({"a": [3], "b": [4]})})
    loaded = read_upload("book.xlsx", content)
    assert loaded.data["a"].tolist() == [1]


def test_combines_excel_sheets_and_records_source():
    content = excel_bytes({"Jan": pd.DataFrame({"a": [1], "b": [2]}),
                           "Feb": pd.DataFrame({"a": [3], "b": [4]})})
    loaded = read_upload("book.xlsx", content, sheets=["Jan", "Feb"])
    assert loaded.data["a"].tolist() == [1, 3]
    assert loaded.data["SourceSheet"].tolist() == ["Jan", "Feb"]


def test_sheets_with_different_columns_cannot_be_combined():
    content = excel_bytes({"Jan": pd.DataFrame({"a": [1], "b": [2]}),
                           "Feb": pd.DataFrame({"x": [3], "y": [4]})})
    with pytest.raises(UploadError, match="different columns"):
        read_upload("book.xlsx", content, sheets=["Jan", "Feb"])
