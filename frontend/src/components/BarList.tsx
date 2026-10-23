import type { ReactNode } from "react";
import type { CountRow } from "../api";
import { fmtNumber } from "../format";

/** Ranked horizontal bars: one hue (magnitude), value and share printed beside each bar. */
export function BarList({
  title,
  rows,
  renderKey = (k) => k,
  empty = "No clicks yet",
}: {
  title: string;
  rows: CountRow[];
  renderKey?: (key: string) => ReactNode;
  empty?: string;
}) {
  const total = rows.reduce((s, r) => s + r.count, 0);
  const max = rows[0]?.count ?? 0;
  return (
    <section className="card p-4 sm:p-5">
      <h2 className="mb-3 text-sm font-semibold text-ink">{title}</h2>
      {rows.length === 0 ? (
        <p className="py-6 text-center text-sm text-ink-3">{empty}</p>
      ) : (
        <ul className="space-y-0.5">
          {rows.map((r) => {
            const share = total ? Math.round((r.count / total) * 100) : 0;
            return (
              <li
                key={r.key}
                className="group relative flex items-center gap-3 rounded-md px-2 py-1.5 hover:bg-sunken"
                title={`${r.key}: ${fmtNumber(r.count)} clicks (${share}%)`}
              >
                <div
                  className="absolute inset-y-1 left-0 rounded-r"
                  style={{
                    width: `${Math.max(2, (r.count / max) * 100)}%`,
                    background: "var(--bar)",
                    opacity: 0.35,
                  }}
                  aria-hidden
                />
                <span className="relative min-w-0 flex-1 truncate text-sm text-ink">{renderKey(r.key)}</span>
                <span className="tabular relative text-sm font-medium text-ink">{fmtNumber(r.count)}</span>
                <span className="tabular relative w-9 text-right text-xs text-ink-3">{share}%</span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
