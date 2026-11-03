import InvoiceDetails from "./InvoiceDetails";
import BankStatementDetails from "./BankStatementDetails";
import ReceiptDetails from "./ReceiptDetails";

type Props = {
  title: string;
  data: unknown;
};

type DataObject = Record<string, unknown>;

function isObject(value: unknown): value is DataObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function getObject(value: unknown): DataObject {
  return isObject(value) ? value : {};
}

function getArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function Field({
  label,
  value,
}: {
  label: string;
  value: unknown;
}) {
  return (
    <div className="rounded-lg bg-gray-50 p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 break-words text-sm font-medium text-gray-900">
        {value === null || value === undefined || value === ""
          ? "—"
          : String(value)}
      </p>
    </div>
  );
}

function Status({ value }: { value: unknown }) {
  const status = String(value ?? "unknown");

  const color =
    status === "completed"
      ? "bg-green-100 text-green-700"
      : status === "failed"
        ? "bg-red-100 text-red-700"
        : "bg-yellow-100 text-yellow-700";

  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${color}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}

export default function ApiResult({ title, data }: Props) {
  const root = getObject(data);

//   const isDocument = Boolean(root.document_id && root.filename);

  const isDocument = Boolean(
    root.document_id &&
    root.filename &&
    (root.ai_extraction || root.extraction_result)
    );

  const invoice = getObject(root.ai_extraction);
  const lineItems = getArray(invoice.line_items);
  const extraction = getObject(root.extraction_result);
  const job = getObject(root.job);

  const results = getArray(root.results);
  const issues = getArray(root.issues);


  const verification = getObject(root.verification);
  const verifiedDocuments = getArray(root.documents);
  const mismatchedRecords = getArray(verification.mismatched_records);
  const matchedRecords = getArray(verification.matched_records);
  const missingFromDoc1 = getArray(verification.missing_from_document_1);
  const missingFromDoc2 = getArray(verification.missing_from_document_2);
  const reviewReasons = getArray(verification.review_reasons);

  return (
    <div className="mt-5 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-semibold text-gray-900">{title}</h3>

        {root.processing_status !== undefined && (
          <Status value={root.processing_status} />
        )}
      </div>

      {isDocument && (
        <>
          <div>
            <h4 className="mb-3 text-sm font-semibold">Document Information</h4>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Filename" value={root.filename} />
              <Field label="Document ID" value={root.document_id} />
              <Field label="File Type" value={root.file_type} />
              <Field label="Category" value={root.document_category} />
              <Field label="Document Type" value={root.document_type} />
              <Field label="File Size (bytes)" value={root.file_size_bytes} />
            </div>
          </div>

          <div>
            <h4 className="mb-3 text-sm font-semibold">Extracted Document Details</h4>

            {/* <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Invoice Number" value={invoice.invoice_number} />
              <Field label="Invoice Date" value={invoice.invoice_date} />
              <Field label="Due Date" value={invoice.due_date} />
              <Field label="Supplier" value={invoice.supplier} />
              <Field label="Customer" value={invoice.customer} />
              <Field label="Currency" value={invoice.currency} />
              <Field label="Subtotal" value={invoice.subtotal} />
              <Field label="Tax Rate" value={invoice.tax_rate} />
              <Field label="Tax Amount" value={invoice.tax_amount} />
              <Field label="Total" value={invoice.total} />
              <Field label="Requires Review" value={invoice.requires_review === undefined ? "—" : invoice.requires_review ? "Yes" : "No"} />
            </div> */}

            {root.document_category === "invoice" && (
                <InvoiceDetails data={root} />
            )}

            {root.document_category === "bank_statement" && (
                <BankStatementDetails data={root} />
            )}

            {root.document_category === "receipt" && (
                <ReceiptDetails data={root} />
            )}

            {root.document_category !== "invoice" &&
                root.document_category !== "bank_statement" && 
                  root.document_category !== "receipt" && (
                    <p className="text-sm text-gray-500">
                        No document-specific display is available for this category.
                    </p>
            )}
          </div>

          {/* <div>
            <h4 className="mb-3 text-sm font-semibold">
              Invoice Line Items ({lineItems.length})
            </h4>

            {lineItems.length > 0 ? (
              <div className="overflow-x-auto rounded-lg border border-gray-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-50 text-gray-600">
                    <tr>
                      <th className="px-4 py-3">Description</th>
                      <th className="px-4 py-3">Quantity</th>
                      <th className="px-4 py-3">Unit Price</th>
                      <th className="px-4 py-3">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lineItems.map((item, index) => {
                      const row = getObject(item);

                      return (
                        <tr key={index} className="border-t border-gray-100">
                          <td className="px-4 py-3">{String(row.description ?? "—")}</td>
                          <td className="px-4 py-3">{String(row.quantity ?? "—")}</td>
                          <td className="px-4 py-3">{String(row.unit_price ?? "—")}</td>
                          <td className="px-4 py-3">{String(row.amount ?? "—")}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-gray-500">No line items available.</p>
            )}
          </div> */}

          <div className="space-y-3">
            <h4 className="text-sm font-semibold">Extraction Information</h4>
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Extraction Method" value={getArray(extraction.pages).length ? getObject(getArray(extraction.pages)[0]).extraction_method : "—"} />
              {/* <Field label="Extraction Method" value={extraction.extraction_method} /> */}
              <Field label="Total Pages" value={extraction.total_pages} />
              <Field label="Pages Requiring Review" value={getArray(extraction.pages_requiring_review).length} />
            </div>
          </div>

          <details className="rounded-lg border border-gray-200 p-4">
            <summary className="cursor-pointer text-sm font-semibold">
              View Extracted OCR Text
            </summary>
            <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap text-xs leading-6 text-gray-700">
              {String(root.extracted_text ?? "No OCR text available.")}
            </pre>
          </details>

          <details className="rounded-lg border border-gray-200 p-4">
            <summary className="cursor-pointer text-sm font-semibold">
              View Complete API JSON
            </summary>
            <pre className="mt-3 max-h-96 overflow-auto text-xs leading-6">
              {JSON.stringify(data, null, 2)}
            </pre>
          </details>
        </>
      )}

      
        {root.verification && (
            <div className="space-y-5">
                <div>
                <h4 className="mb-3 text-sm font-semibold">
                    Document Verification Summary
                </h4>

                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    <Field
                    label="Verification ID"
                    value={root.verification_id}
                    />
                    <Field
                    label="Document Category"
                    value={verification.document_category}
                    />
                    <div className="rounded-lg bg-gray-50 p-3">
                    <p className="text-xs text-gray-500">Verification Status</p>
                    <div className="mt-2">
                        <Status value={verification.verification_status} />
                    </div>
                    </div>
                    <Field
                    label="Matched Records"
                    value={matchedRecords.length}
                    />
                    <Field
                    label="Mismatched Records"
                    value={mismatchedRecords.length}
                    />
                    <Field
                    label="Requires Review"
                    value={verification.requires_review ? "Yes" : "No"}
                    />
                </div>
                </div>

                <div>
                <h4 className="mb-3 text-sm font-semibold">
                    Submitted Documents
                </h4>

                <div className="space-y-3">
                    {verifiedDocuments.map((item, index) => {
                    const doc = getObject(item);

                    return (
                        <div
                        key={index}
                        className="rounded-lg border border-gray-200 p-4"
                        >
                        <p className="font-medium text-gray-900">
                            {String(doc.filename ?? "Document")}
                        </p>

                        <p className="mt-1 break-all text-xs text-gray-500">
                            ID: {String(doc.document_id ?? "—")}
                        </p>

                        <div className="mt-3">
                            <Status value={doc.processing_status} />
                        </div>
                        </div>
                    );
                    })}
                </div>
                </div>

                <div>
                <h4 className="mb-3 text-sm font-semibold">
                    Record Matching
                </h4>

                <div className="space-y-3">
                    {mismatchedRecords.map((item, index) => {
                    const record = getObject(item);
                    const doc1 = getObject(record.document_1_record);
                    const doc2 = getObject(record.document_2_record);
                    const mismatches = getObject(record.mismatched_fields);

                    return (
                        <div
                        key={index}
                        className="rounded-lg border border-amber-200 p-4"
                        >
                        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                            <h5 className="font-medium">
                            Mismatched Record {index + 1}
                            </h5>
                            <Status value="requires_review" />
                        </div>

                        <div className="grid gap-3 md:grid-cols-2">
                            <div className="rounded-lg bg-gray-50 p-3">
                            <p className="mb-2 text-xs font-semibold text-gray-600">
                                Document 1: {String(verification.document_1 ?? "—")}
                            </p>
                            <p className="text-sm">
                                Supplier: {String(doc1.supplier ?? "—")}
                            </p>
                            <p className="mt-1 text-sm">
                                Customer: {String(doc1.customer ?? "—")}
                            </p>
                            <p className="mt-1 text-sm">
                                Invoice Number: {String(doc1.invoice_number ?? "—")}
                            </p>
                            </div>

                            <div className="rounded-lg bg-gray-50 p-3">
                            <p className="mb-2 text-xs font-semibold text-gray-600">
                                Document 2: {String(verification.document_2 ?? "—")}
                            </p>
                            <p className="text-sm">
                                Supplier: {String(doc2.supplier ?? "—")}
                            </p>
                            <p className="mt-1 text-sm">
                                Customer: {String(doc2.customer ?? "—")}
                            </p>
                            <p className="mt-1 text-sm">
                                Invoice Number: {String(doc2.invoice_number ?? "—")}
                            </p>
                            </div>
                        </div>

                        <h5 className="mb-2 mt-5 text-sm font-semibold">
                            Field-by-Field Differences
                        </h5>

                        <div className="overflow-x-auto rounded-lg border border-gray-200">
                            <table className="w-full text-left text-sm">
                            <thead className="bg-gray-50 text-gray-600">
                                <tr>
                                <th className="px-3 py-3">Field</th>
                                <th className="px-3 py-3">Document 1</th>
                                <th className="px-3 py-3">Document 2</th>
                                </tr>
                            </thead>
                            <tbody>
                                {Object.entries(mismatches).map(([field, values]) => {
                                const difference = getObject(values);

                                return (
                                    <tr key={field} className="border-t border-gray-100">
                                    <td className="px-3 py-3 font-medium">
                                        {field.replaceAll("_", " ")}
                                    </td>
                                    <td className="px-3 py-3 text-red-600">
                                        {String(difference.document_1 ?? "—")}
                                    </td>
                                    <td className="px-3 py-3 text-blue-700">
                                        {String(difference.document_2 ?? "—")}
                                    </td>
                                    </tr>
                                );
                                })}
                            </tbody>
                            </table>
                        </div>

                        {getArray(record.matching_fields).length > 0 && (
                            <div className="mt-3">
                            <p className="text-xs font-semibold text-green-700">
                                Matching Fields
                            </p>
                            <p className="mt-1 text-sm">
                                {getArray(record.matching_fields).map(String).join(", ")}
                            </p>
                            </div>
                        )}
                        </div>
                    );
                    })}

                    {matchedRecords.length > 0 && (
                    <div className="rounded-lg border border-green-200 bg-green-50 p-4">
                        <p className="font-medium text-green-800">
                        {matchedRecords.length} matching record(s) found.
                        </p>
                    </div>
                    )}

                    {mismatchedRecords.length === 0 && matchedRecords.length === 0 && (
                    <p className="text-sm text-gray-500">
                        No matching or mismatching records were returned.
                    </p>
                    )}
                </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                {[
                    {
                    title: "Missing from Document 1",
                    items: missingFromDoc1,
                    },
                    {
                    title: "Missing from Document 2",
                    items: missingFromDoc2,
                    },
                ].map((group) => (
                    <div
                    key={group.title}
                    className="rounded-lg border border-gray-200 p-4"
                    >
                    <h5 className="mb-3 text-sm font-semibold">
                        {group.title} ({group.items.length})
                    </h5>

                    {group.items.length === 0 ? (
                        <p className="text-sm text-gray-500">No missing records.</p>
                    ) : (
                        <div className="space-y-2">
                        {group.items.map((item, index) => {
                            const missing = getObject(item);

                            return (
                            <div
                                key={index}
                                className="rounded-lg bg-gray-50 p-3 text-sm"
                            >
                                <p className="font-medium">
                                {String(missing.description ?? missing.record_type ?? "Missing record")}
                                </p>
                                <p className="mt-1 text-xs text-gray-500">
                                Amount: {String(missing.amount ?? "—")}
                                </p>
                            </div>
                            );
                        })}
                        </div>
                    )}
                    </div>
                ))}
                </div>

                <div>
                <h4 className="mb-3 text-sm font-semibold">
                    Review Reasons
                </h4>

                {reviewReasons.length > 0 ? (
                    <ul className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-4">
                    {reviewReasons.map((reason, index) => (
                        <li key={index} className="text-sm text-amber-800">
                        • {String(reason)}
                        </li>
                    ))}
                    </ul>
                ) : (
                    <p className="text-sm text-gray-500">
                    No review reasons provided.
                    </p>
                )}
                </div>

                <details className="rounded-lg border border-gray-200 p-4">
                <summary className="cursor-pointer text-sm font-semibold">
                    View Complete Verification JSON
                </summary>
                <pre className="mt-3 max-h-96 overflow-auto text-xs leading-6">
                    {JSON.stringify(data, null, 2)}
                </pre>
                </details>
            </div>
        )}


      {root.job && (
        <div>
          <h4 className="mb-3 text-sm font-semibold">Processing Job</h4>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Field label="Job ID" value={job.job_id} />
            <Field label="Task ID" value={job.task_id} />
            <Field label="Job Status" value={job.status} />
            <Field label="Retry Count" value={job.retry_count} />
            <Field label="Maximum Retries" value={job.max_retries} />
            <Field label="Error Message" value={job.error_message} />
            <Field label="Started At" value={job.started_at} />
            <Field label="Completed At" value={job.completed_at} />
          </div>
        </div>
      )}

      {root.total_issues !== undefined && (
        <div>
          <h4 className="mb-3 text-sm font-semibold">Validation Results</h4>
          <p className="mb-3 text-sm text-gray-600">
            Total issues: <strong>{String(root.total_issues)}</strong>
          </p>

          {issues.length === 0 ? (
            <p className="rounded-lg bg-green-50 p-4 text-sm text-green-700">
              No validation issues found.
            </p>
          ) : (
            <div className="space-y-2">
              {issues.map((issue, index) => (
                <pre key={index} className="rounded-lg bg-red-50 p-3 text-xs text-red-700">
                  {JSON.stringify(issue, null, 2)}
                </pre>
              ))}
            </div>
          )}
        </div>
      )}

      {root.total_results !== undefined && (
        <div>
          <h4 className="mb-3 text-sm font-semibold">
            Search Results ({String(root.total_results)})
          </h4>

          <div className="space-y-3">
            {results.map((item, index) => {
              const row = getObject(item);

              return (
                <div key={index} className="rounded-lg border border-gray-200 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-medium">{String(row.filename ?? "Document")}</p>
                    {row.similarity_score !== undefined && (
                      <span className="rounded-full bg-blue-50 px-3 py-1 text-xs text-blue-700">
                        Similarity: {String(row.similarity_score)}
                      </span>
                    )}
                  </div>

                  <div className="mt-2 grid gap-2 text-xs text-gray-500 sm:grid-cols-2">
                    <p>ID: {String(row.document_id ?? "—")}</p>
                    <p>Category: {String(row.document_category ?? "—")}</p>
                    <p>Chunk: {String(row.chunk_index ?? "—")}</p>
                  </div>

                  {row.content !== undefined && (
                    <details className="mt-3">
                      <summary className="cursor-pointer text-sm text-blue-700">
                        View matching content
                      </summary>
                      <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded bg-gray-50 p-3 text-xs leading-5">
                        {String(row.content)}
                      </pre>
                    </details>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {root.total !== undefined && (
        <div>
          <h4 className="mb-3 text-sm font-semibold">
            Matching Documents ({String(root.total)})
          </h4>

          <div className="space-y-3">
            {results.map((item, index) => {
              const row = getObject(item);

              return (
                <div key={index} className="rounded-lg border border-gray-200 p-4">
                  <p className="font-medium">{String(row.filename ?? "Document")}</p>
                  <div className="mt-2 grid gap-2 text-xs text-gray-500 sm:grid-cols-2">
                    <p>ID: {String(row.document_id ?? "—")}</p>
                    <p>Category: {String(row.document_category ?? "—")}</p>
                    <p>File Type: {String(row.file_type ?? "—")}</p>
                    <p>Size: {String(row.file_size_bytes ?? "—")} bytes</p>
                  </div>
                  <div className="mt-3">
                    <Status value={row.processing_status} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!isDocument &&
        root.job === undefined &&
        root.total_issues === undefined &&
        root.total_results === undefined &&
        root.total === undefined && 
        root.verification === undefined && (
          <pre className="max-h-96 overflow-auto rounded-lg bg-gray-950 p-4 text-xs leading-6 text-green-300">
            {JSON.stringify(data, null, 2)}
          </pre>
        )}
    </div>
  );
}
