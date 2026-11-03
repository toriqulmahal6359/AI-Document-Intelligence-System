
type Props = {
  data: Record<string, unknown>;
};

function asObject(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function getArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.map(asObject)
    : [];
}

function Info({
  label,
  value,
}: {
  label: string;
  value: unknown;
}) {
  return (
    <div className="rounded-lg border border-gray-200 p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold text-gray-900">
        {display(value)}
      </p>
    </div>
  );
}

export default function InvoiceDetails({ data }: Props) {
  const invoice = asObject(data.ai_extraction);
  const items = getArray(invoice.line_items);

  return (
    <div className="space-y-5">
      <section>
        <h4 className="mb-3 text-sm font-semibold">
          Extracted Invoice Information
        </h4>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Info label="Invoice Number" value={invoice.invoice_number} />
          <Info label="Invoice Date" value={invoice.invoice_date} />
          <Info label="Due Date" value={invoice.due_date} />
          <Info label="Supplier" value={invoice.supplier} />
          <Info label="Customer" value={invoice.customer} />
          <Info label="Currency" value={invoice.currency} />
          <Info label="Subtotal" value={invoice.subtotal} />
          <Info label="Tax Rate" value={invoice.tax_rate} />
          <Info label="Tax Amount" value={invoice.tax_amount} />
          <Info label="Total" value={invoice.total} />
          <Info
            label="Requires Review"
            value={invoice.requires_review ? "Yes" : "No"}
          />
        </div>
      </section>

      <section>
        <h4 className="mb-3 text-sm font-semibold">
          Invoice Line Items ({items.length})
        </h4>

        {items.length === 0 ? (
          <p className="text-sm text-gray-500">
            No invoice line items available.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="px-3 py-3">Description</th>
                  <th className="px-3 py-3">Quantity</th>
                  <th className="px-3 py-3">Unit Price</th>
                  <th className="px-3 py-3">Amount</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => (
                  <tr key={index} className="border-t border-gray-100">
                    <td className="px-3 py-3">
                      {display(item.description)}
                    </td>
                    <td className="px-3 py-3">
                      {display(item.quantity)}
                    </td>
                    <td className="px-3 py-3">
                      {display(item.unit_price)}
                    </td>
                    <td className="px-3 py-3 font-medium">
                      {display(item.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {Array.isArray(invoice.review_reason) &&
        invoice.review_reason.length > 0 && (
          <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <h4 className="mb-2 text-sm font-semibold text-amber-800">
              Review Reasons
            </h4>
            <ul className="list-disc space-y-1 pl-5 text-sm text-amber-800">
              {invoice.review_reason.map((reason, index) => (
                <li key={index}>{String(reason)}</li>
              ))}
            </ul>
          </section>
        )}
    </div>
  );
}
