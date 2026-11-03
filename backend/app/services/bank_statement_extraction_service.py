import os
import pytesseract
from PIL import Image

import tempfile
from io import BytesIO

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

from app.schemas.bank_statement import BankStatement, BankTransaction
from app.processors.spreadsheet_processor import process_spreadsheet

import re
import pymupdf

pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_CMD", "tesseract"
)

COLUMN_ALIASES = {
    "date": "transaction_date",
    "transaction date": "transaction_date",
    "description": "description",
    "particulars": "description",
    "narration": "description",
    "debit": "debit",
    "withdrawal": "debit",
    "withdrawals": "debit",
    "credit": "credit",
    "deposit": "credit",
    "deposits": "credit",
    "balance": "balance",
    "running balance": "balance",
}


def parse_amount(value: Any):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None

    if isinstance(value, str):
        value = value.replace(",", "").replace("₹", "").strip()

        if value.startswith("(") and value.endswith(")"):
            value = "-" + value[1:-1]

    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"Invalid financial amount: {value}")


def parse_date(value: Any):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    # parsed = pd.to_datetime(value, dayfirst=False, errors="coerce")

    date_text = str(value).strip()

    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", date_text):
        parsed = pd.to_datetime(
            date_text,
            format="%Y-%m-%d",
            errors="coerce",
        )
    else:
        parsed = pd.to_datetime(
            date_text,
            dayfirst=True,
            errors="coerce",
        )

    if pd.isna(parsed):
        raise ValueError(f"Invalid transaction date: {value}")

    return parsed.date()

## statement metadata excution


# def extract_statement_metadata(text: str) -> dict:
#     """Extract labelled bank statement metadata from digital PDF text."""

#     def get_label_value(label: str):
#         pattern = rf"(?im)^\s*{re.escape(label)}\s*:?\s*\n\s*(.*?)\s*$"
#         match = re.search(pattern, text)
#         return match.group(1).strip() if match else None

#     def get_amount(label: str):
#         value = get_label_value(label)
#         if not value:
#             return None

#         try:
#             return parse_amount(value)
#         except (ValueError, InvalidOperation):
#             return None

#     account_holder = get_label_value("Account holder")
#     account_number = get_label_value("Account number")
#     account_type = get_label_value("Account type")
#     branch = get_label_value("Branch")

#     statement_period = get_label_value("Statement period")
#     start_date = None
#     end_date = None

#     if statement_period:
#         dates = re.findall(
#             r"\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{1,2}-\d{1,2}",
#             statement_period,
#         )

#         if len(dates) >= 2:
#             start_date = parse_date(dates[0])
#             end_date = parse_date(dates[1])

#     currency = None

#     if "₹" in text or re.search(r"\bINR\b|Indian rupees", text, re.I):
#         currency = "INR"
#     elif "$" in text or re.search(r"\bUSD\b", text, re.I):
#         currency = "USD"
#     elif "৳" in text or re.search(r"\bBDT\b", text, re.I):
#         currency = "BDT"
#     elif "£" in text or re.search(r"\bGBP\b", text, re.I):
#         currency = "GBP"
#     elif "€" in text or re.search(r"\bEUR\b", text, re.I):
#         currency = "EUR"

#     return {
#         "account_holder": account_holder,
#         "account_number": account_number,
#         "account_type": account_type,
#         "branch": branch,
#         "statement_start_date": start_date,
#         "statement_end_date": end_date,
#         "currency": currency,
#         "opening_balance": get_amount("Opening balance"),
#         "total_debits": get_amount("Total debits"),
#         "total_credits": get_amount("Total credits"),
#         "closing_balance": get_amount("Closing balance"),
#     }

def extract_statement_metadata(text: str) -> dict:
    """Extract labelled metadata from digital PDF or OCR text."""

    labels = [
        "Account holder",
        "Account number",
        "Account type",
        "Statement period",
        "Address",
        "Branch",
        "Opening balance",
        "Total debits",
        "Total credits",
        "Closing balance",
    ]

    label_pattern = "|".join(
        re.escape(label) for label in labels
    )

    normalized_text = re.sub(r"[ \t]+", " ", text)

    def get_label_value(label: str):
        # rf"(?=\s+(?:{label_pattern})\s*:?\s*|$)"
        pattern = (
            rf"(?is)\b{re.escape(label)}\s*:?\s*"
            rf"(.*?)"
            rf"(?=\s+(?:{label_pattern})\s*:?\s*|[\r\n]|$)"
        )

        match = re.search(pattern, normalized_text)

        if match:
            value = match.group(1).strip()
            return value or None

        return None

    def get_amount(label: str):
        value = get_label_value(label)

        if not value:
            return None

        # Remove OCR-confused currency symbols before parsing.
        value = re.sub(r"^[^\d(+-]+", "", value)

        try:
            return parse_amount(value)
        except (ValueError, InvalidOperation):
            return None

    account_holder = get_label_value("Account holder")
    account_number = get_label_value("Account number")
    account_type = get_label_value("Account type")
    branch = get_label_value("Branch")

    statement_period = get_label_value("Statement period")

    start_date = None
    end_date = None

    if statement_period:
        dates = re.findall(
            r"\d{1,2}[/-]\d{1,2}[/-]\d{4}"
            r"|\d{4}-\d{1,2}-\d{1,2}",
            statement_period,
        )

        if len(dates) >= 2:
            start_date = parse_date(dates[0])
            end_date = parse_date(dates[1])

    currency = None

    if "₹" in text or re.search(
        r"\bINR\b|Indian rupees", text, re.I
    ):
        currency = "INR"
    elif "৳" in text or re.search(r"\bBDT\b", text, re.I):
        currency = "BDT"
    elif "£" in text or re.search(r"\bGBP\b", text, re.I):
        currency = "GBP"
    elif "€" in text or re.search(r"\bEUR\b", text, re.I):
        currency = "EUR"
    elif "$" in text or re.search(r"\bUSD\b", text, re.I):
        currency = "USD"

    return {
        "account_holder": account_holder,
        "account_number": account_number,
        "account_type": account_type,
        "branch": branch,
        "statement_start_date": start_date,
        "statement_end_date": end_date,
        "currency": currency,
        "opening_balance": get_amount("Opening balance"),
        "total_debits": get_amount("Total debits"),
        "total_credits": get_amount("Total credits"),
        "closing_balance": get_amount("Closing balance"),
    }



def normalize_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.copy()

    normalized = {}

    for column in dataframe.columns:
        key = str(column).strip().lower()
        normalized[column] = COLUMN_ALIASES.get(key, key)

    dataframe = dataframe.rename(columns=normalized)

    required = {"transaction_date", "description", "debit", "credit", "balance"}
    missing = required - set(dataframe.columns)

    if missing:
        raise ValueError(
            f"Missing required bank statement columns: {sorted(missing)}"
        )

    return dataframe


def extract_bank_statement(
    dataframe: pd.DataFrame,
    metadata: dict | None = None,
) -> BankStatement:

    metadata = metadata or {}

    dataframe = normalize_columns(dataframe)

    # transactions = []

    # for _, row in dataframe.iterrows():
    #     transactions.append(
    #         BankTransaction(
    #             transaction_date=parse_date(row["transaction_date"]),
    #             description=(
    #                 str(row["description"]).strip()
    #                 if pd.notna(row["description"])
    #                 else None
    #             ),
    #             debit=parse_amount(row["debit"]),
    #             credit=parse_amount(row["credit"]),
    #             balance=parse_amount(row["balance"]),
    #         )
    #     )

    transactions = []

    for _, row in dataframe.iterrows():

        # Ignore completely empty rows
        if row.isna().all():
            continue

        transaction_date = parse_date(row["transaction_date"])
        description = (
            str(row["description"]).strip()
            if pd.notna(row["description"])
            else None
        )

        debit = parse_amount(row["debit"])
        credit = parse_amount(row["credit"])
        balance = parse_amount(row["balance"])

        # Ignore rows without any transaction information
        if not any([
            transaction_date,
            description,
            debit is not None,
            credit is not None,
            balance is not None,
        ]):
            continue

        transactions.append(
            BankTransaction(
                transaction_date=transaction_date,
                description=description,
                debit=debit,
                credit=credit,
                balance=balance,
            )
        )

    return BankStatement(
        account_holder=metadata.get("account_holder"),
        account_number=metadata.get("account_number"),
        account_type=metadata.get("account_type"),
        branch=metadata.get("branch"),
        statement_start_date=metadata.get("statement_start_date"),
        statement_end_date=metadata.get("statement_end_date"),
        currency=metadata.get("currency"),
        opening_balance=parse_amount(metadata.get("opening_balance")),
        total_debits=parse_amount(metadata.get("total_debits")),
        total_credits=parse_amount(metadata.get("total_credits")),
        closing_balance=parse_amount(metadata.get("closing_balance")),
        transactions=transactions,
    )

# def extract_bank_statement_from_spreadsheet(
#     file_path: str,
#     metadata: dict | None = None,
#     sheet_name: str | None = None,
# ) -> BankStatement:

#     # Read the spreadsheet using the existing processor
#     spreadsheet = process_spreadsheet(file_path)

#     sheets = spreadsheet["sheets"]

#     if not sheets:
#         raise ValueError("Spreadsheet contains no readable sheets.")

#     # Select the requested sheet, or the first sheet by default
#     selected_sheet = sheet_name or next(iter(sheets))

#     if selected_sheet not in sheets:
#         raise ValueError(
#             f"Sheet '{selected_sheet}' not found. "
#             f"Available sheets: {list(sheets.keys())}"
#         )

#     # Convert extracted records back into a DataFrame
#     records = sheets[selected_sheet]["records"]
#     dataframe = pd.DataFrame(
#         records,
#         columns=sheets[selected_sheet]["columns"],
#     )

#     # Perform document-specific extraction
#     return extract_bank_statement(
#         dataframe=dataframe,
#         metadata=metadata,
#     )

def extract_bank_statement_from_spreadsheet(
    file_path: str,
    metadata: dict | None = None,
    sheet_name: str | None = None,
) -> BankStatement:

    spreadsheet = process_spreadsheet(file_path)
    sheets = spreadsheet["sheets"]

    if not sheets:
        raise ValueError("Spreadsheet contains no readable sheets.")

    if sheet_name:
        if sheet_name not in sheets:
            raise ValueError(
                f"Sheet '{sheet_name}' not found. "
                f"Available sheets: {list(sheets.keys())}"
            )

        candidate_sheets = [sheet_name]

    else:
        candidate_sheets = list(sheets.keys())

    required = {
        "transaction_date",
        "description",
        "debit",
        "credit",
        "balance",
    }

    sheet_errors = []

    for current_sheet in candidate_sheets:

        sheet_data = sheets[current_sheet]

        dataframe = pd.DataFrame(
            sheet_data["records"],
            columns=sheet_data["columns"],
        )

        try:
            normalized_dataframe = normalize_columns(dataframe)

            missing = required - set(normalized_dataframe.columns)

            if missing:
                raise ValueError(
                    f"Missing columns: {sorted(missing)}"
                )

            return extract_bank_statement(
                dataframe=dataframe,
                metadata=metadata,
            )

        except ValueError as exc:
            sheet_errors.append(
                f"{current_sheet}: {exc}"
            )

    raise ValueError(
        "No suitable bank transaction sheet was found. "
        + " | ".join(sheet_errors)
    )


def extract_ocr_words_from_pdf_page(page, scale: float = 2.0):
    """
    Extract OCR words and their bounding boxes from a scanned PDF page.
    Coordinates are converted back to PDF page coordinates.
    """

    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(scale, scale),
        colorspace=pymupdf.csGRAY,
        alpha=False,
    )

    image = Image.frombytes(
        "L",
        [pixmap.width, pixmap.height],
        pixmap.samples,
    )

    data = pytesseract.image_to_data(
        image,
        output_type=pytesseract.Output.DICT,
        config="--oem 3 --psm 3",
    )

    words = []
    lines = {}

    for index, text in enumerate(data["text"]):
        text = text.strip()

        if not text:
            continue

        try:
            confidence = float(data["conf"][index])
        except (ValueError, TypeError):
            continue

        if confidence < 0:
            continue

        left = data["left"][index] / scale
        top = data["top"][index] / scale
        right = (
            data["left"][index] + data["width"][index]
        ) / scale
        bottom = (
            data["top"][index] + data["height"][index]
        ) / scale

        block_number = data["block_num"][index]
        paragraph_number = data["par_num"][index]
        line_number = data["line_num"][index]

        words.append((
            left,
            top,
            right,
            bottom,
            text,
            block_number,
            line_number,
            data["word_num"][index],
        ))

        line_key = (
            block_number,
            paragraph_number,
            line_number,
        )

        lines.setdefault(line_key, []).append(
            (data["word_num"][index], text)
        )

    words.sort(key=lambda word: (word[1], word[0]))

    page_text = "\n".join(
        " ".join(
            word for _, word in sorted(line_words)
        )
        for _, line_words in sorted(lines.items())
    )

    return words, page_text

def extract_bank_statement_from_pdf(file_path: str, metadata: dict | None = None) -> BankStatement:
    """
    Extract transaction rows from a digital PDF using table column coordinates.
    The table headers are detected dynamically on each page.
    """

    date_pattern = re.compile(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b"
    )

    required_headers = {"date", "description", "debit", "credit", "balance"}
    transactions = []

    with pymupdf.open(file_path) as pdf:
        metadata_text_parts = []
        for page_number, page in enumerate(pdf, start=1):

            # metadata_text_parts.append(page.get_text("text"))

            # words = page.get_text("words", sort=True)

            page_text = page.get_text("text").strip()
            words = page.get_text("words", sort=True)

            # Use OCR when embedded PDF text is insufficient.
            if len(page_text) < 30 or len(words) < 5:
                print(
                    f"Page {page_number}: using Tesseract OCR."
                )

                words, page_text = extract_ocr_words_from_pdf_page(page)

            metadata_text_parts.append(page_text)

            # Locate the table header on this page.
            header_positions = {}

            for word in words:
                label = word[4].lower().strip(":").strip()

                if label in required_headers:
                    header_positions[label] = {
                        "x": (word[0] + word[2]) / 2,
                        "y": (word[1] + word[3]) / 2,
                    }


            # # Locate the table header on this page.
            # if not required_headers.issubset(header_positions):
            #     print(f"Page {page_number}: table header not found; skipping.")
            #     continue

            # Locate the actual table header by finding all five labels
            # on the same horizontal line.
            header_rows = []

            for word in words:
                label = word[4].lower().strip(":").strip()

                if label not in required_headers:
                    continue

                y_center = (word[1] + word[3]) / 2

                matching_row = next(
                    (
                        row for row in header_rows
                        if abs(row["y"] - y_center) <= 3
                    ),
                    None,
                )

                if matching_row is None:
                    matching_row = {"y": y_center, "labels": {}}
                    header_rows.append(matching_row)

                matching_row["labels"][label] = {
                    "x": (word[0] + word[2]) / 2,
                    "y": y_center,
                }

            valid_headers = [
                row for row in header_rows
                if required_headers.issubset(row["labels"])
            ]

            if not valid_headers:
                print(f"Page {page_number}: table header not found; skipping.")
                continue

            header_positions = min(
                valid_headers,
                key=lambda row: row["y"],
            )["labels"]

            # Determine column boundaries from the header positions.
            columns = sorted(
                [(position["x"], name) for name, position in header_positions.items()]
            )

            boundaries = [
                (columns[i][0] + columns[i + 1][0]) / 2
                for i in range(len(columns) - 1)
            ]

            header_y = max(
                position["y"] for position in header_positions.values()
            )

            # Group words into visual rows using their vertical coordinates.
            page_rows = []

            for word in words:
                x0, y0, x1, y1, text = word[:5]
                y_center = (y0 + y1) / 2

                if y_center <= header_y + 5:
                    continue

                if not page_rows or abs(y_center - page_rows[-1]["y"]) > 3:
                    page_rows.append({
                        "y": y_center,
                        "words": []
                    })

                page_rows[-1]["words"].append(word)

            # Assign each word to its corresponding column.
            for row in page_rows:
                cells = {
                    "date": [],
                    "description": [],
                    "debit": [],
                    "credit": [],
                    "balance": [],
                }

                for word in sorted(row["words"], key=lambda item: item[0]):
                    x0, y0, x1, y1, text = word[:5]
                    x_center = (x0 + x1) / 2

                    column_index = sum(
                        x_center > boundary for boundary in boundaries
                    )

                    column_name = columns[column_index][1]
                    cells[column_name].append(text)

                date_text = " ".join(cells["date"])
                date_match = date_pattern.search(date_text)

                # A transaction row must contain a recognizable date.
                if not date_match:
                    continue

                transaction_date = parse_date(date_match.group(0))

                if not transaction_date:
                    continue

                description = " ".join(cells["description"]).strip()

                # Exclude statement summary rows from transaction records.
                description_normalized = description.lower().strip()

                if description_normalized in {
                    "opening balance",
                    "closing balance",
                    "total",
                    "total debits",
                    "total credits",
                }:
                    continue

                transaction = BankTransaction(
                    transaction_date=transaction_date,
                    description=description or None,
                    debit=parse_amount(" ".join(cells["debit"])),
                    credit=parse_amount(" ".join(cells["credit"])),
                    balance=parse_amount(" ".join(cells["balance"])),
                )

                transactions.append(transaction)

    # statement_metadata = dict(metadata or {})
    # statement_metadata.pop("transactions", None)

    # statement = BankStatement(
    #     **statement_metadata,
    #     transactions=transactions,
    # )

    # Extract metadata from the text collected across all PDF pages.
    extracted_metadata = extract_statement_metadata(
        "\n".join(metadata_text_parts)
    )

    # Explicitly supplied metadata takes precedence.
    statement_metadata = {
        **extracted_metadata,
        **(metadata or {}),
    }

    statement_metadata.pop("transactions", None)

    statement = BankStatement(
        **statement_metadata,
        transactions=transactions,
    )

    print(
        f"PDF extraction completed: "
        f"{len(transactions)} transaction rows extracted."
    )

    return statement

def extract_bank_statement_from_image(
    file_path: str,
    metadata: dict | None = None,
) -> BankStatement:
    """
    Extract a bank statement image using the existing PDF
    coordinate-based parser and Tesseract OCR.
    """

    image_path = os.path.abspath(file_path)

    if not os.path.isfile(image_path):
        raise FileNotFoundError(
            f"Bank statement image not found: {image_path}"
        )

    # Load and validate the image before creating the temporary PDF.
    try:
        with Image.open(image_path) as image:
            image.load()
            image = image.convert("RGB")

            width, height = image.size

            image_buffer = BytesIO()
            image.save(image_buffer, format="PNG")
            image_bytes = image_buffer.getvalue()

    except Exception as exc:
        raise ValueError(
            f"Unable to read bank statement image: {exc}"
        ) from exc

    if width <= 0 or height <= 0:
        raise ValueError("Bank statement image has invalid dimensions.")

    temporary_pdf_path = None

    try:
        # Create a temporary PDF with the image as its only page.
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as temporary_pdf:
            temporary_pdf_path = temporary_pdf.name

        with pymupdf.open() as pdf:
            page = pdf.new_page(
                width=width / 2,
                height=height / 2,
            )

            page.insert_image(
                page.rect,
                stream=image_bytes,
            )

            pdf.save(temporary_pdf_path)

        # Reuse the existing PDF extraction and OCR implementation.
        return extract_bank_statement_from_pdf(
            file_path=temporary_pdf_path,
            metadata=metadata,
        )

    finally:
        # Always remove the temporary PDF.
        if (
            temporary_pdf_path
            and os.path.exists(temporary_pdf_path)
        ):
            os.remove(temporary_pdf_path)
