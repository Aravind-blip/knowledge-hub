import Link from "next/link";


type EmptyStateProps = {
  title: string;
  description: string;
  actionHref?: string;
  actionLabel?: string;
};

export function EmptyState({ title, description, actionHref, actionLabel }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-state__badge">Knowledge Hub</div>
      <h2>{title}</h2>
      <p>{description}</p>
      {actionHref && actionLabel ? (
        <Link className="button button--primary" href={actionHref}>
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}

