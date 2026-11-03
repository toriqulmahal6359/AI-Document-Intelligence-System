type Props = {
  data: Record<string, unknown>;
};

type Transaction = {
  transaction_date?: string | null;
  description?: string | null;
  debit?: string | number | null;
  credit?: string | number | null;
  balance?: string | number | null;
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

// HELPER VALIDATION
function formatValidationItem(value: unknown): string {
  if (typeof value !== "object" || value === null) {
    return display(value);
  }

  const item = asObject(value);

  const issue = display(item.issue);
  const details = [
    item.calculated !== undefined
      ? `Calculated: ${display(item.calculated)}`
      : null,
    item.reported !== undefined
      ? `Reported: ${display(item.reported)}`
      : null,
    item.difference !== undefined
      ? `Difference: ${display(item.difference)}`
      : null,
  ].filter(Boolean);

  return details.length > 0
    ? `${issue} (${details.join(" | ")})`
    : issue;
}

function amount(value: unknown): number {
  if (value === null || value === undefined || value === "") return 0;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatAmount(value: unknown, currency: string): string {
  const parsed = amount(value);

  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(parsed);
  } catch {
    return `${currency} ${parsed.toFixed(2)}`;
  }
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
      <p className="mt-1 break-words text-sm font-medium text-gray-900">
        {display(value)}
      </p>
    </div>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-gray-900">
        {value}
      </p>
    </div>
  );
}

export default function BankStatementDetails({ data }: Props) {
  const statement = asObject(data.ai_extraction);
  const validation = asObject(data.validation_result);

  const currency = String(statement.currency ?? "INR");
  const transactions = Array.isArray(statement.transactions)
    ? (statement.transactions as Transaction[])
    : [];

  const debitTransactions = transactions.filter(
    (item) => amount(item.debit) > 0
  );

  const creditTransactions = transactions.filter(
    (item) => amount(item.credit) > 0
  );

  const totalDebits = amount(statement.total_debits);
  const totalCredits = amount(statement.total_credits);

  const averageDebit =
    debitTransactions.length > 0
      ? totalDebits / debitTransactions.length
      : 0;

  const averageCredit =
    creditTransactions.length > 0
      ? totalCredits / creditTransactions.length
      : 0;

  const largestDebit = Math.max(
    0,
    ...debitTransactions.map((item) => amount(item.debit))
  );

  const largestCredit = Math.max(
    0,
    ...creditTransactions.map((item) => amount(item.credit))
  );

  const netCashFlow = totalCredits - totalDebits;

  const reviewReasons = Array.isArray(statement.review_reason)
    ? statement.review_reason
    : [];

  const validationErrors = Array.isArray(validation.errors)
    ? validation.errors
    : [];

  const validationWarnings = Array.isArray(validation.warnings)
    ? validation.warnings
    : [];

  return (
    <div className="space-y-6">

      {/* Account Information */}
      <section className="space-y-3">
        <h4 className="text-sm font-semibold">
          Bank Account Information
        </h4>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Info label="Account Holder" value={statement.account_holder} />
          <Info label="Account Number" value={statement.account_number} />
          <Info label="Account Type" value={statement.account_type} />
          <Info label="Branch" value={statement.branch} />
          <Info label="Currency" value={currency} />
          <Info label="Statement Start Date" value={statement.statement_start_date} />
          <Info label="Statement End Date" value={statement.statement_end_date} />
        </div>
      </section>

      {/* Balance Summary */}
      <section className="space-y-3">
        <h4 className="text-sm font-semibold">
          Statement Summary
        </h4>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Metric
            label="Opening Balance"
            value={formatAmount(statement.opening_balance, currency)}
          />
          <Metric
            label="Closing Balance"
            value={formatAmount(statement.closing_balance, currency)}
          />
          <Metric
            label="Total Debits"
            value={formatAmount(statement.total_debits, currency)}
          />
          <Metric
            label="Total Credits"
            value={formatAmount(statement.total_credits, currency)}
          />
          <Metric
            label="Average Debit"
            value={formatAmount(averageDebit, currency)}
          />
          <Metric
            label="Average Credit"
            value={formatAmount(averageCredit, currency)}
          />
          <Metric
            label="Largest Debit"
            value={formatAmount(largestDebit, currency)}
          />
          <Metric
            label="Largest Credit"
            value={formatAmount(largestCredit, currency)}
          />
          <Metric
            label="Net Cash Flow"
            value={formatAmount(netCashFlow, currency)}
          />
        </div>
      </section>

      {/* Transaction Counts */}
      <section className="space-y-3">
        <h4 className="text-sm font-semibold">
          Transaction Overview
        </h4>

        <div className="grid gap-3 sm:grid-cols-3">
          <Metric
            label="Total Transactions"
            value={String(transactions.length)}
          />
          <Metric
            label="Debit Transactions"
            value={String(debitTransactions.length)}
          />
          <Metric
            label="Credit Transactions"
            value={String(creditTransactions.length)}
          />
        </div>
      </section>

      {/* Transaction History */}
      <section className="space-y-3">
        <h4 className="text-sm font-semibold">
          Transaction History ({transactions.length})
        </h4>

        {transactions.length > 0 ? (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="whitespace-nowrap px-4 py-3">Date</th>
                  <th className="px-4 py-3">Description</th>
                  <th className="whitespace-nowrap px-4 py-3 text-right">Debit</th>
                  <th className="whitespace-nowrap px-4 py-3 text-right">Credit</th>
                  <th className="whitespace-nowrap px-4 py-3 text-right">Balance</th>
                </tr>
              </thead>

              <tbody>
                {transactions.map((item, index) => (
                  <tr key={index} className="border-t border-gray-100">
                    <td className="whitespace-nowrap px-4 py-3">
                      {display(item.transaction_date)}
                    </td>
                    <td className="px-4 py-3">
                      {display(item.description)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right">
                      {item.debit != null
                        ? formatAmount(item.debit, currency)
                        : "—"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right">
                      {item.credit != null
                        ? formatAmount(item.credit, currency)
                        : "—"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right">
                      {formatAmount(item.balance, currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-500">
            No transactions available.
          </p>
        )}
      </section>

      {/* Validation Results */}
      <section className="space-y-3">
        <h4 className="text-sm font-semibold">
          Financial Validation
        </h4>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Info label="Validation Status" value={validation.status} />
          <Info
            label="Requires Review"
            value={validation.requires_review === true ? "Yes" : "No"}
          />
          <Info
            label="Calculated Closing Balance"
            value={formatAmount(validation.calculated_closing_balance, currency)}
          />
        </div>

        {validationErrors.length > 0 && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3">
            <p className="mb-2 text-sm font-semibold text-red-700">
              Validation Errors
            </p>
            {validationErrors.map((error, index) => (
              <p key={index} className="text-sm text-red-600">
                {/* {String(error)} */}
                {formatValidationItem(error)}
              </p>
            ))}
          </div>
        )}

        {validationWarnings.length > 0 && (
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3">
            <p className="mb-2 text-sm font-semibold text-yellow-700">
              Validation Warnings
            </p>
            {validationWarnings.map((warning, index) => (
              <p key={index} className="text-sm text-yellow-700">
                {/* {String(warning)} */}
                {formatValidationItem(warning)}
              </p>
            ))}
          </div>
        )}

        {reviewReasons.length > 0 && (
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3">
            <p className="mb-2 text-sm font-semibold text-yellow-700">
              Review Reasons
            </p>
            {reviewReasons.map((reason, index) => (
              <p key={index} className="text-sm text-yellow-700">
                {String(reason)}
              </p>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
