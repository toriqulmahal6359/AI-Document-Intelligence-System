
"use client";

import { useState } from "react";
import {
  uploadDocuments,
  verifyDocuments,
  getDocumentStatus,
  searchDocuments,
  semanticSearchDocuments,
  correctInvoice,
  retryDocument,
  getVerification,
  getDocumentValidationIssues,
  getDocument,
  type InvoiceCorrection,
} from "@/lib/api";

import ApiResult from "@/components/ApiResult";

type Result = {
  title: string;
  data: unknown;
};

const emptyCorrection: InvoiceCorrection = {
  invoice_number: null,
  invoice_date: null,
  due_date: null,
  supplier: null,
  customer: null,
  currency: null,
  subtotal: null,
  tax_rate: null,
  tax_amount: null,
  total: null,
  line_items: [],
};

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");

  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [category, setCategory] = useState("invoice");

  const [verifyFile1, setVerifyFile1] = useState<File | null>(null);
  const [verifyFile2, setVerifyFile2] = useState<File | null>(null);

  const [verifyCategory1, setVerifyCategory1] = useState("invoice");
  const [verifyCategory2, setVerifyCategory2] = useState("invoice");

  const [searchQuery, setSearchQuery] = useState("");
  const [searchMode, setSearchMode] = useState<"keyword" | "semantic">(
    "keyword"
  );

  const [documentId, setDocumentId] = useState("");
  const [verificationId, setVerificationId] = useState("");

  const [correctionJson, setCorrectionJson] = useState(
    JSON.stringify(emptyCorrection, null, 2)
  );

  async function execute(
    title: string,
    operation: () => Promise<unknown>
  ) {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const data = await operation();
      setResult({ title, data });
    } catch (err) {
      console.error("API Request Error:", err);
      
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred."
      );
    } finally {
      setLoading(false);
    }
  }

  const inputClass =
    "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

  const buttonClass =
    "rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50";

  const secondaryButtonClass =
    "rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50";

  function documentAction(
    title: string,
    action: (id: string) => Promise<unknown>
  ) {
    if (!documentId.trim()) {
      setError("Please enter a document ID.");
      return;
    }

    execute(title, () => action(documentId.trim()));
  }

  return (
    <main className="min-h-screen bg-gray-50 text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              Document Intelligence
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              AI-powered document processing and verification
            </p>
          </div>

          <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
            API Dashboard
          </span>
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-8 px-6 py-8">
        {/* Upload */}
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">1. Upload Documents</h2>
          <p className="mt-1 text-sm text-gray-500">
            Upload one or multiple documents for processing.
          </p>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium">
                Document Category
              </label>
              <select
                className={inputClass}
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="invoice">Invoice</option>
                <option value="bank_statement">Bank Statement</option>
                <option value="receipt">Receipt</option>
                {/* <option value="bank_statement">Reciept</option> */}
                {/* <option value="identity">Identity Document</option> */}
                {/* <option value="contract">Contract</option> */}
                {/* <option value="other">Other</option> */}
              </select>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Select Files
              </label>
              <input
                className={inputClass}
                type="file"
                multiple
                onChange={(e) =>
                  setUploadFiles(Array.from(e.target.files || []))
                }
              />
            </div>
          </div>

          {uploadFiles.length > 0 && (
            <p className="mt-3 text-sm text-gray-500">
              {uploadFiles.length} file(s) selected
            </p>
          )}

          <button
            className={`${buttonClass} mt-4`}
            disabled={loading || uploadFiles.length === 0}
            onClick={() =>
              execute("Upload Documents", () =>
                uploadDocuments(uploadFiles, category)
              )
            }
          >
            Upload Documents
          </button>
        </section>

        {/* Verification */}
        {/* <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">2. Verify Documents</h2>
          <p className="mt-1 text-sm text-gray-500">
            Compare two documents using the verification API.
          </p>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium">
                First Document
              </label>
              <input
                type="file"
                className={inputClass}
                onChange={(e) =>
                  setVerifyFile1(e.target.files?.[0] || null)
                }
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Second Document
              </label>
              <input
                type="file"
                className={inputClass}
                onChange={(e) =>
                  setVerifyFile2(e.target.files?.[0] || null)
                }
              />
            </div>
          </div>

          <button
            className={`${buttonClass} mt-4`}
            disabled={loading || !verifyFile1 || !verifyFile2}
            onClick={() => {
              if (!verifyFile1 || !verifyFile2) return;

              execute("Document Verification", () =>
                verifyDocuments(verifyFile1, verifyFile2, category)
              );
            }}
          >
            Verify Documents
          </button>
        </section> */}

        {/* Verification */}
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">2. Verify Documents</h2>
          <p className="mt-1 text-sm text-gray-500">
            Compare two documents using the verification API.
          </p>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium">
                First Document
              </label>
              <input
                type="file"
                className={inputClass}
                onChange={(e) =>
                  setVerifyFile1(e.target.files?.[0] || null)
                }
              />

              <label className="mb-2 mt-3 block text-sm font-medium">
                First Document Category
              </label>
              <select
                className={inputClass}
                value={verifyCategory1}
                onChange={(e) => setVerifyCategory1(e.target.value)}
              >
                <option value="invoice">Invoice</option>
                <option value="bank_statement">Bank Statement</option>
                <option value="receipt">Receipt</option>
              </select>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Second Document
              </label>
              <input
                type="file"
                className={inputClass}
                onChange={(e) =>
                  setVerifyFile2(e.target.files?.[0] || null)
                }
              />

              <label className="mb-2 mt-3 block text-sm font-medium">
                Second Document Category
              </label>
              <select
                className={inputClass}
                value={verifyCategory2}
                onChange={(e) => setVerifyCategory2(e.target.value)}
              >
                <option value="invoice">Invoice</option>
                <option value="bank_statement">Bank Statement</option>
                <option value="receipt">Receipt</option>
              </select>
            </div>
          </div>

          <button
            className={`${buttonClass} mt-4`}
            disabled={loading || !verifyFile1 || !verifyFile2}
            onClick={() => {
              if (!verifyFile1 || !verifyFile2) return;

              execute("Document Verification", () =>
                verifyDocuments(
                  verifyFile1,
                  verifyFile2,
                  verifyCategory1,
                  verifyCategory2
                )
              );
            }}
          >
            Verify Documents
          </button>
        </section>

        {/* Search */}
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">3. Search Documents</h2>
          <p className="mt-1 text-sm text-gray-500">
            Search by keywords or use semantic search.
          </p>

          <div className="mt-5 flex flex-wrap gap-3">
            <button
              className={
                searchMode === "keyword"
                  ? buttonClass
                  : secondaryButtonClass
              }
              onClick={() => setSearchMode("keyword")}
            >
              Keyword Search
            </button>

            <button
              className={
                searchMode === "semantic"
                  ? buttonClass
                  : secondaryButtonClass
              }
              onClick={() => setSearchMode("semantic")}
            >
              Semantic Search
            </button>
          </div>

          <div className="mt-4 flex flex-col gap-3 sm:flex-row">
            <input
              className={inputClass}
              placeholder="Enter your search query..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />

            <button
              className={buttonClass}
              disabled={loading || searchQuery.trim().length < 2}
              onClick={() =>
                execute(
                  searchMode === "keyword"
                    ? "Keyword Search Results"
                    : "Semantic Search Results",
                  () =>
                    searchMode === "keyword"
                      ? searchDocuments({
                          q: searchQuery.trim(),
                          limit: 20,
                          offset: 0,
                        })
                      : semanticSearchDocuments(searchQuery.trim())
                )
              }
            >
              Search
            </button>
          </div>
        </section>

        {/* Document operations */}
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">4. Document Management</h2>
          <p className="mt-1 text-sm text-gray-500">
            Retrieve document details, check processing status, and manage
            validation.
          </p>

          <div className="mt-5">
            <label className="mb-2 block text-sm font-medium">
              Document ID
            </label>
            <input
              className={inputClass}
              placeholder="Enter document ID"
              value={documentId}
              onChange={(e) => setDocumentId(e.target.value)}
            />
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <button
              className={buttonClass}
              disabled={loading}
              onClick={() =>
                documentAction("Document Details", getDocument)
              }
            >
              Get Document
            </button>

            <button
              className={secondaryButtonClass}
              disabled={loading}
              onClick={() =>
                documentAction("Document Status", getDocumentStatus)
              }
            >
              Check Status
            </button>

            <button
              className={secondaryButtonClass}
              disabled={loading}
              onClick={() =>
                documentAction(
                  "Validation Issues",
                  getDocumentValidationIssues
                )
              }
            >
              Validation Issues
            </button>

            <button
              className={secondaryButtonClass}
              disabled={loading}
              onClick={() =>
                documentAction("Retry Processing", retryDocument)
              }
            >
              Retry Processing
            </button>
          </div>
        </section>

        {/* Invoice correction */}
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">5. Invoice Correction</h2>
          <p className="mt-1 text-sm text-gray-500">
            Submit corrected invoice fields as JSON.
          </p>

          <label className="mb-2 mt-5 block text-sm font-medium">
            Correction JSON
          </label>

          <textarea
            className={`${inputClass} min-h-80 font-mono text-xs`}
            spellCheck={false}
            value={correctionJson}
            onChange={(e) => setCorrectionJson(e.target.value)}
          />

          <button
            className={`${buttonClass} mt-4`}
            disabled={loading || !documentId.trim()}
            onClick={() => {
              try {
                const corrections = JSON.parse(
                  correctionJson
                ) as InvoiceCorrection;

                execute("Invoice Correction", () =>
                  correctInvoice(documentId.trim(), corrections)
                );
              } catch {
                setError("Invalid JSON. Please check your correction data.");
              }
            }}
          >
            Submit Corrections
          </button>

          <p className="mt-2 text-xs text-gray-500">
            Uses the Document ID entered in the Document Management section.
          </p>
        </section>

        {/* Verification lookup */}
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">6. Verification Details</h2>
          <p className="mt-1 text-sm text-gray-500">
            Retrieve a previously created verification record.
          </p>

          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <input
              className={inputClass}
              placeholder="Enter verification ID"
              value={verificationId}
              onChange={(e) => setVerificationId(e.target.value)}
            />

            <button
              className={buttonClass}
              disabled={loading || !verificationId.trim()}
              onClick={() =>
                execute("Verification Details", () =>
                  getVerification(verificationId.trim())
                )
              }
            >
              Get Verification
            </button>
          </div>
        </section>

        {/* API response */}
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">API Response</h2>
              <p className="mt-1 text-sm text-gray-500">
                Results and errors from backend requests appear here.
              </p>
            </div>

            {(result || error) && (
              <button
                className={secondaryButtonClass}
                onClick={() => {
                  setResult(null);
                  setError("");
                }}
              >
                Clear
              </button>
            )}
          </div>

          {loading && (
            <p className="mt-5 text-sm font-medium text-blue-600">
              Processing request...
            </p>
          )}

          {error && (
            <div className="mt-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              <strong>Request failed:</strong> {error}
            </div>
          )}

          {result && (
              <ApiResult
                    title={result.title}
                    data={result.data}
              />
          )}

          {!loading && !error && !result && (
            <div className="mt-5 rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-400">
              No API response yet. Perform an operation to see its result.
            </div>
          )}
        </section>

        <footer className="pb-4 text-center text-xs text-gray-400">
          AI-Powered Document Intelligence System
        </footer>
      </div>
    </main>
  );
}
