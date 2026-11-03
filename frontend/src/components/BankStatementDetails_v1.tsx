
type Props = {
  data: Record<string, unknown>;
};

type Transaction = Record<string, unknown>;

function asObject(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function firstValue(
  object: Record<string, unknown>,
  keys: string[]
): unknown {
  for (const key of keys) {
    const value = object[key];
    if (value !== undefined && value !== null && value !== "") {
      return value;
    }
  }
  return undefined;
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function numeric(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value !== "string") return null;

  const cleaned = value.replace(/[₹$€£,\s]/g, "").trim();
  if (!cleaned) return null;

  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatAmount(value: number | null, currency: string): string {
  if (value === null) return "—";

  return `${currency ? currency + " " : ""}${value.toLocaleString(
    "en-IN",
    {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }
  )}`;
}

function getTransactions(source: Record<string, unknown>): Transaction[] {
  const value = firstValue(source, [
    "transactions",
    "transaction_history",
    "statement_transactions",
    "entries",
    "records",
  ]);

  return Array.isArray(value) ? value.map(asObject) : [];
}

function transactionAmount(
  transaction: Transaction,
  keys: string[]
): number {
  return numeric(firstValue(transaction, keys)) ?? 0;
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

function Metric({
  label,
  value,
  description,
}: {
  label: string;
  value: string;
  description?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-2 text-xl font-bold text-gray-900">{value}</p>
      {description && (
        <p className="mt-1 text-xs text-gray-500">{description}</p>
      )}
    </div>
  );
}

export default function BankStatementDetails({ data }: Props) {
  const extraction = asObject(data.ai_extraction);

  // Support common nested extraction response structures.
  const nested = asObject(
    extraction.bank_statement ??
      extraction.statement ??
      extraction.extracted_data
  );

  const statement = { ...extraction, ...nested };
  const transactions = getTransactions(statement);

  const currency = display(
    firstValue(statement, ["currency", "currency_code"])
  );
  const currencyLabel = currency === "—" ? "" : currency;

  const debitKeys = ["debit", "debit_amount", "withdrawal", "withdrawals"];
  const creditKeys = ["credit", "credit_amount", "deposit", "deposits"];

  const transactionRows = transactions.filter((transaction) => {
    const description = String(
      firstValue(transaction, ["description", "narration", "particulars"]) ?? ""
    ).toLowerCase();

    return (
      !description.includes("opening balance") &&
      !description.includes("closing balance")
    );
  });

  const debitTransactions = transactionRows
    .map((transaction) => transactionAmount(transaction, debitKeys))
    .filter((amount) => amount > 0);

  const creditTransactions = transactionRows
    .map((transaction) => transactionAmount(transaction, creditKeys))
    .filter((amount) => amount > 0);

  const calculatedDebits = debitTransactions.reduce(
    (total, amount) => total + amount,
    0
  );

  const calculatedCredits = creditTransactions.reduce(
    (total, amount) => total + amount,
    0
  );

  const extractedDebits = numeric(
    firstValue(statement, ["total_debits", "total_debit", "debit_total"])
  );

  const extractedCredits = numeric(
    firstValue(statement, ["total_credits", "total_credit", "credit_total"])
  );

  const totalDebits = extractedDebits ?? (
    transactions.length > 0 ? calculatedDebits : null
  );

  const totalCredits = extractedCredits ?? (
    transactions.length > 0 ? calculatedCredits : null
  );

  const averageDebit =
    debitTransactions.length > 0
      ? calculatedDebits / debitTransactions.length
      : null;

  const averageCredit =
    creditTransactions.length > 0
      ? calculatedCredits / creditTransactions.length
      : null;

  const netCashFlow =
    totalDebits !== null && totalCredits !== null
      ? totalCredits - totalDebits
      : null;

  const largestDebit =
    debitTransactions.length > 0
      ? Math.max(...debitTransactions)
      : null;

  const largestCredit =
    creditTransactions.length > 0
      ? Math.max(...creditTransactions)
      : null;

  const openingBalance = firstValue(statement, [
    "opening_balance",
    "start_balance",
  ]);

  const closingBalance = firstValue(statement, [
    "closing_balance",
    "ending_balance",
    "end_balance",
  ]);

  return (
    <div className="space-y-6">
      <section>
        <h4 className="mb-3 text-sm font-semibold">
          Bank Account Information
        </h4>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Info
            label="Bank Name"
            value={firstValue(statement, ["bank_name", "bank", "institution"])}
          />
          <Info
            label="Account Holder"
            value={firstValue(statement, ["account_holder", "account_name"])}
          />
          <Info
            label="Account Number"
            value={firstValue(statement, ["account_number", "account_no"])}
          />
          <Info
            label="Account Type"
            value={firstValue(statement, ["account_type", "account_category"])}
          />
          <Info
            label="Branch"
            value={firstValue(statement, ["branch", "branch_name"])}
          />
          <Info label="Currency" value={currency} />
          <Info
            label="Statement Start Date"
            value={firstValue(statement, [
              "statement_start_date",
              "start_date",
              "period_start",
            ])}
          />
          <Info
            label="Statement End Date"
            value={firstValue(statement, [
              "statement_end_date",
              "end_date",
              "period_end",
            ])}
          />
        </div>
      </section>

      <section>
        <h4 className="mb-3 text-sm font-semibold">
          Financial Summary
        </h4>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric
            label="Total Credits"
            value={formatAmount(totalCredits, currencyLabel)}
          />
          <Metric
            label="Total Debits"
            value={formatAmount(totalDebits, currencyLabel)}
          />
          <Metric
            label="Opening Balance"
            value={display(openingBalance)}
          />
          <Metric
            label="Closing Balance"
            value={display(closingBalance)}
          />
        </div>
      </section>

      <section>
        <h4 className="mb-3 text-sm font-semibold">
          Transaction Analytics
        </h4>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Metric
            label="Average Credit"
            value={formatAmount(averageCredit, currencyLabel)}
            description={`${creditTransactions.length} credit transactions`}
          />
          <Metric
            label="Average Debit"
            value={formatAmount(averageDebit, currencyLabel)}
            description={`${debitTransactions.length} debit transactions`}
          />
          <Metric
            label="Net Cash Flow"
            value={formatAmount(netCashFlow, currencyLabel)}
          />
          <Metric
            label="Largest Credit"
            value={formatAmount(largestCredit, currencyLabel)}
          />
          <Metric
            label="Largest Debit"
            value={formatAmount(largestDebit, currencyLabel)}
          />
          <Metric
            label="Total Transactions"
            value={String(transactionRows.length)}
          />
        </div>

        <p className="mt-2 text-xs text-gray-500">
          Averages are calculated from extracted transaction rows. Opening
          and closing balance rows are excluded.
        </p>
      </section>

      <section>
        <h4 className="mb-3 text-sm font-semibold">
          Transaction History ({transactionRows.length})
        </h4>

        {transactionRows.length === 0 ? (
          <p className="text-sm text-gray-500">
            No structured transaction records were returned by the backend.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="px-3 py-3">Date</th>
                  <th className="px-3 py-3">Description</th>
                  <th className="px-3 py-3">Debit</th>
                  <th className="px-3 py-3">Credit</th>
                  <th className="px-3 py-3">Balance</th>
                </tr>
              </thead>
              <tbody>
                {transactionRows.map((transaction, index) => (
                  <tr key={index} className="border-t border-gray-100">
                    <td className="whitespace-nowrap px-3 py-3">
                      {display(
                        firstValue(transaction, ["date", "transaction_date"])
                      )}
                    </td>
                    <td className="min-w-48 px-3 py-3">
                      {display(
                        firstValue(transaction, [
                          "description",
                          "narration",
                          "particulars",
                        ])
                      )}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-red-600">
                      {display(firstValue(transaction, debitKeys))}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-green-700">
                      {display(firstValue(transaction, creditKeys))}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3">
                      {display(
                        firstValue(transaction, ["balance", "running_balance"])
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {Array.isArray(statement.review_reason) &&
        statement.review_reason.length > 0 && (
          <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <h4 className="mb-2 text-sm font-semibold text-amber-800">
              Review Reasons
            </h4>
            <ul className="list-disc space-y-1 pl-5 text-sm text-amber-800">
              {statement.review_reason.map((reason, index) => (
                <li key={index}>{String(reason)}</li>
              ))}
            </ul>
          </section>
        )}
    </div>
  );
}
