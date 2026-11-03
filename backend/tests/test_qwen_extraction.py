import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


from app.services.extraction_service import extract_invoice


sample_text = """
Larkfield Stationers
TAX INVOICE

Invoice no. INV-2026-0142
Invoice date 18 September 2026

BILL TO
Example Traders

Subtotal 14,702.00
GST at 18% 2,646.36
Total due 17,348.36

ITEMS
A4 copier paper, 75 gsm, ream of 500
20 x 285.00 = 5,700.00

Ballpoint pens, blue, box of 50
4 x 420.00 = 1,680.00

Lever-arch files, A4, pack of 10
3 x 899.00 = 2,697.00

Whiteboard markers, assorted, pack of 4
6 x 160.00 = 960.00

Desk organiser, mesh, black
5 x 349.00 = 1,745.00

Sticky notes, 76 x 76 mm, pack of 12
8 x 240.00 = 1,920.00
"""


if __name__ == "__main__":
    invoice = extract_invoice(sample_text)

    print(invoice.model_dump_json(indent=2))
