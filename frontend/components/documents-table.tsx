import Link from "next/link";

import type { DocumentRecord } from "@/types";
import { formatBytes, formatDate } from "@/lib/utils";
import { ListPagination } from "@/components/list-pagination";


export function DocumentsTable({
  documents,
  page,
  pageSize,
  total,
}: {
  documents: DocumentRecord[];
  page: number;
  pageSize: number;
  total: number;
}) {
  return (
    <div className="panel">
      <div className="panel__header">
        <div>
          <h2>Indexed files</h2>
          <p>Current organization document inventory, ingestion status, and source readiness.</p>
        </div>
        <Link className="button button--secondary" href="/documents/upload">
          Upload documents
        </Link>
      </div>
      <ListPagination basePath="/documents" page={page} pageSize={pageSize} total={total} />
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>File</th>
              <th>Status</th>
              <th>Type</th>
              <th>Size</th>
              <th>Processed</th>
              <th>Chunks</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((document) => (
              <tr key={document.id}>
                <td>
                  <div className="table-title">{document.original_name}</div>
                  <div className="table-subtitle">{document.file_name}</div>
                </td>
                <td>
                  <span className={`status-pill status-pill--${document.status}`}>{document.status}</span>
                </td>
                <td>{document.content_type}</td>
                <td>{formatBytes(document.file_size)}</td>
                <td>{formatDate(document.created_at)}</td>
                <td>{String(document.metadata?.chunk_count ?? "—")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
