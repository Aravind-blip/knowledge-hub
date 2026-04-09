type Metric = {
  label: string;
  value: string;
  detail: string;
};


export function MetricGrid({ metrics }: { metrics: Metric[] }) {
  return (
    <div className="metric-grid">
      {metrics.map((metric) => (
        <article className="metric-card" key={metric.label}>
          <p className="metric-card__label">{metric.label}</p>
          <p className="metric-card__value">{metric.value}</p>
          <p className="metric-card__detail">{metric.detail}</p>
        </article>
      ))}
    </div>
  );
}

