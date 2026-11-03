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
  return Array.isArray(value) ? value.map(asObject) : [];
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

export default function ReceiptDetails({ data }: Props) {
  const receipt = asObject(data.ai_extraction);
  const items = getArray(receipt.line_items);

  return (
    <div className="space-y-5">
      <section>
        <h4 className="mb-3 text-sm font-semibold">
          Extracted Receipt Information
        </h4>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Info label="Merchant Name" value={receipt.merchant_name} />
          <Info label="Receipt Number" value={receipt.receipt_number} />
          <Info label="Receipt Date" value={receipt.receipt_date} />
          <Info label="Currency" value={receipt.currency} />
          <Info label="Subtotal" value={receipt.subtotal} />
          <Info label="Tax Amount" value={receipt.tax_amount} />
          <Info label="Total Amount" value={receipt.total} />
          <Info label="Payment Method" value={receipt.payment_method} />
          <Info
            label="Requires Review"
            value={receipt.requires_review ? "Yes" : "No"}
          />
        </div>
      </section>

      <section>
        <h4 className="mb-3 text-sm font-semibold">
          Receipt Line Items ({items.length})
        </h4>

        {items.length === 0 ? (
          <p className="text-sm text-gray-500">
            No receipt line items available.
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

      {Array.isArray(receipt.review_reason) &&
        receipt.review_reason.length > 0 && (
          <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <h4 className="mb-2 text-sm font-semibold text-amber-800">
              Review Reasons
            </h4>
            <ul className="list-disc space-y-1 pl-5 text-sm text-amber-800">
              {receipt.review_reason.map((reason, index) => (
                <li key={index}>{String(reason)}</li>
              ))}
            </ul>
          </section>
        )}
    </div>
  );
}
