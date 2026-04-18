export default function DashboardLoading() {
  return (
    <section className="page">
      <div className="page-header page-header--loading">
        <div className="skeleton-block skeleton-block--eyebrow" />
        <div className="skeleton-block skeleton-block--title" />
        <div className="skeleton-block skeleton-block--description" />
      </div>
      <div className="metric-grid">
        {Array.from({ length: 3 }).map((_, index) => (
          <article className="metric-card metric-card--skeleton" key={index}>
            <div className="skeleton-block skeleton-block--label" />
            <div className="skeleton-block skeleton-block--value" />
            <div className="skeleton-block skeleton-block--detail" />
          </article>
        ))}
      </div>
      <div className="panel panel--skeleton">
        <div className="skeleton-block skeleton-block--table-header" />
        <div className="skeleton-table">
          {Array.from({ length: 5 }).map((_, index) => (
            <div className="skeleton-table__row" key={index}>
              <div className="skeleton-block skeleton-block--table-cell" />
              <div className="skeleton-block skeleton-block--table-cell" />
              <div className="skeleton-block skeleton-block--table-cell" />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
