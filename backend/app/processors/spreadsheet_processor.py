
from pathlib import Path

import pandas as pd


SUPPORTED_FORMATS = {".xlsx", ".xls", ".csv"}


def process_spreadsheet(file_path: str) -> dict:
    """
    Extract spreadsheet data into JSON-compatible dictionaries.
    Supports CSV, XLSX and XLS files.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    extension = path.suffix.lower()

    if extension not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported spreadsheet format: {extension}")

    sheets = {}

    try:
        if extension == ".csv":
            dataframe = _read_csv(path)
            sheets["Sheet1"] = _convert_dataframe(dataframe)

        else:
            excel_file = pd.ExcelFile(path)

            for sheet_name in excel_file.sheet_names:
                dataframe = pd.read_excel(
                    excel_file,
                    sheet_name=sheet_name,
                )

                sheets[sheet_name] = _convert_dataframe(dataframe)

    except Exception as exc:
        raise ValueError(
            f"Unable to process spreadsheet {path.name}: {exc}"
        ) from exc

    total_rows = sum(
        sheet["row_count"] for sheet in sheets.values()
    )

    return {
        "filename": path.name,
        "file_type": extension,
        "sheet_count": len(sheets),
        "total_rows": total_rows,
        "sheets": sheets,
    }


def _read_csv(path: Path) -> pd.DataFrame:
    """Read CSV with common encoding fallbacks."""

    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1"]

    for encoding in encodings:
        try:
            return pd.read_csv(
                path,
                encoding=encoding,
                on_bad_lines="error",
            )
        except UnicodeDecodeError:
            continue

    raise ValueError("Unable to determine CSV file encoding.")


def _convert_dataframe(dataframe: pd.DataFrame) -> dict:
    """Convert a DataFrame into JSON-compatible records."""

    dataframe = dataframe.astype(object)
    dataframe = dataframe.where(pd.notna(dataframe), None)

    records = dataframe.to_dict(orient="records")

    return {
        "columns": [str(column) for column in dataframe.columns],
        "row_count": len(records),
        "records": records,
    }
