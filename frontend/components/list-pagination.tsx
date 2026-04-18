import Link from "next/link";

type ListPaginationProps = {
  basePath: string;
  page: number;
  pageSize: number;
  total: number;
};

export function ListPagination({ basePath, page, pageSize, total }: ListPaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const previousPage = Math.max(1, page - 1);
  const nextPage = Math.min(totalPages, page + 1);
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(total, page * pageSize);

  return (
    <div className="list-pagination">
      <p className="list-pagination__meta">
        Showing {start}-{end} of {total}
      </p>
      <div className="list-pagination__actions">
        <Link
          aria-disabled={page <= 1}
          className={`button button--secondary ${page <= 1 ? "button--disabled" : ""}`}
          href={`${basePath}?page=${previousPage}`}
          tabIndex={page <= 1 ? -1 : undefined}
        >
          Previous
        </Link>
        <span className="list-pagination__page">
          Page {page} of {totalPages}
        </span>
        <Link
          aria-disabled={page >= totalPages}
          className={`button button--secondary ${page >= totalPages ? "button--disabled" : ""}`}
          href={`${basePath}?page=${nextPage}`}
          tabIndex={page >= totalPages ? -1 : undefined}
        >
          Next
        </Link>
      </div>
    </div>
  );
}
