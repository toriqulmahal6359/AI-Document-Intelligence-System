
const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

export type ApiResponse = unknown;

export interface InvoiceLineItem {
  description: string | null;
  quantity: number | string | null;
  unit_price: number | string | null;
  amount: number | string | null;
}

export interface InvoiceCorrection {
  invoice_number: string | null;
  invoice_date: string | null;
  due_date: string | null;
  supplier: string | null;
  customer: string | null;
  currency: string | null;
  subtotal: number | string | null;
  tax_rate: number | string | null;
  tax_amount: number | string | null;
  total: number | string | null;
  line_items: InvoiceLineItem[];
}

// async function request<T = ApiResponse>(
//   path: string,
//   options: RequestInit = {}
// ): Promise<T> {
//   const response = await fetch(`${API_BASE_URL}${path}`, options);

//   const contentType = response.headers.get("content-type") || "";
//   let result: unknown = null;

//   if (response.status !== 204) {
//     result = contentType.includes("application/json")
//       ? await response.json()
//       : await response.text();
//   }

//   if (!response.ok) {
//     const message =
//       typeof result === "object" &&
//       result !== null &&
//       "detail" in result
//         ? String((result as { detail: unknown }).detail)
//         : typeof result === "string" && result
//           ? result
//           : `Request failed (${response.status})`;

//     throw new Error(message);
//   }

//   return result as T;
// }


async function request<T = ApiResponse>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);

  const contentType = response.headers.get("content-type") || "";
  let result: unknown = null;

  if (response.status !== 204) {
    result = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
  }

  if (!response.ok) {
    const message =
      typeof result === "object" &&
      result !== null &&
      "detail" in result
        ? typeof (result as { detail: unknown }).detail === "string"
          ? (result as { detail: string }).detail
          : JSON.stringify((result as { detail: unknown }).detail, null, 2)
        : typeof result === "string" && result
          ? result
          : JSON.stringify(result) || `Request failed (${response.status})`;

    throw new Error(message);
  }

  return result as T;
}

// 1. Upload Documents
export async function uploadDocuments(
  files: File[],
  documentCategory?: string
) {
  const formData = new FormData();

  files.forEach((file) => formData.append("files", file));

  if (documentCategory) {
    formData.append("document_category", documentCategory);
  }

  return request("/api/documents/upload", {
    method: "POST",
    body: formData,
  });
}

// 2. Verify Uploaded Documents
// export async function verifyDocuments(
//   document1: File,
//   document2: File,
//   documentCategory: string
// ) {
//   const formData = new FormData();

//   formData.append("document_1", document1);
//   formData.append("document_2", document2);
//   formData.append("document_category", documentCategory);

//   return request("/api/documents/verify", {
//     method: "POST",
//     body: formData,
//   });
// }

// 2. Verify Uploaded Documents
export async function verifyDocuments(
  document1: File,
  document2: File,
  document1Category: string,
  document2Category: string
) {
  const formData = new FormData();

  formData.append("document_1", document1);
  formData.append("document_2", document2);
  formData.append("document_1_category", document1Category);
  formData.append("document_2_category", document2Category);

  return request("/api/documents/verify", {
    method: "POST",
    body: formData,
  });
}

// 3. Get Document Status
export async function getDocumentStatus(documentId: string) {
  return request(
    `/api/documents/${encodeURIComponent(documentId)}/status`
  );
}

// 4. Search Documents
export interface DocumentSearchParams {
  q?: string;
  document_category?: string;
  processing_status?: string;
  limit?: number;
  offset?: number;
}

export async function searchDocuments(
  params: DocumentSearchParams = {}
) {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });

  return request(
    `/api/documents/search?${query.toString()}`
  );
}

// 5. Semantic Search Documents
export async function semanticSearchDocuments(
  q: string,
  limit = 10
) {
  const query = new URLSearchParams({
    q,
    limit: String(limit),
  });

  return request(
    `/api/documents/semantic-search?${query.toString()}`
  );
}

// 6. Correct Invoice
export async function correctInvoice(
  documentId: string,
  corrections: InvoiceCorrection
) {
  return request(
    `/api/documents/${encodeURIComponent(documentId)}/corrections`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(corrections),
    }
  );
}

// 7. Retry Document Processing
export async function retryDocument(documentId: string) {
  return request(
    `/api/documents/${encodeURIComponent(documentId)}/retry`,
    {
      method: "POST",
    }
  );
}

// 8. Get Verification Details
export async function getVerification(verificationId: string) {
  return request(
    `/api/documents/verifications/${encodeURIComponent(verificationId)}`
  );
}

// 9. Get Document Validation Issues
export async function getDocumentValidationIssues(
  documentId: string
) {
  return request(
    `/api/documents/${encodeURIComponent(documentId)}/validation-issues`
  );
}

// 10. Get Document Details
export async function getDocument(documentId: string) {
  return request(
    `/api/documents/${encodeURIComponent(documentId)}`
  );
}
