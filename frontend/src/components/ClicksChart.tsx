import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DayRow } from "../api";
import { fmtCompact, fmtDay, fmtNumber } from "../format";
import { Segmented } from "./ui";

// Visitors is dashed and drawn first, so the clicks line stays visible when the two are equal.
const SERIES = [
  { key: "clicks", label: "Clicks", color: "var(--series-1)", dash: undefined },
  { key: "visitors", label: "Unique visitors", color: "var(--series-2)", dash: "5 4" },
] as const;

function Swatch({ color, dash }: { color: string; dash?: string }) {
  return (
    <svg width="16" height="4" aria-hidden className="shrink-0">
      <line x1="0" y1="2" x2="16" y2="2" stroke={color} strokeWidth="2" strokeDasharray={dash ? "4 3" : undefined} />
    </svg>
  );
}

type TipProps = { active?: boolean; label?: string; payload?: { dataKey: string; value: number }[] };

function ChartTooltip({ active, label, payload }: TipProps) {
  if (!active || !payload?.length || !label) return null;
  return (
    <div className="rounded-lg border border-line bg-card px-3 py-2 text-xs shadow-lg">
      <div className="mb-1 font-medium text-ink">{fmtDay(label)}</div>
      {SERIES.map((s) => {
        const v = payload.find((p) => p.dataKey === s.key)?.value ?? 0;
        return (
          <div key={s.key} className="flex items-center gap-2 text-ink-2">
            <Swatch color={s.color} dash={s.dash} />
            <span>{s.label}</span>
            <span className="tabular ml-auto pl-4 font-medium text-ink">{fmtNumber(v)}</span>
          </div>
        );
      })}
    </div>
  );
}

export function ClicksChart({ data, title = "Clicks over time" }: { data: DayRow[]; title?: string }) {
  const [view, setView] = useState<"chart" | "table">("chart");
  const ticks = data.length > 14 ? Math.ceil(data.length / 7) : 1;

  return (
    <section className="card p-4 sm:p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          <div className="mt-1 flex gap-4 text-xs text-ink-2">
            {SERIES.map((s) => (
              <span key={s.key} className="inline-flex items-center gap-1.5">
                <Swatch color={s.color} dash={s.dash} />
                {s.label}
              </span>
            ))}
          </div>
        </div>
        <Segmented
          label="Display as"
          value={view}
          onChange={setView}
          options={[
            { value: "chart", label: "Chart" },
            { value: "table", label: "Table" },
          ]}
        />
      </div>

      {view === "chart" ? (
        <div className="h-60 w-full" role="img" aria-label={`${title}: line chart of daily clicks and visitors`}>
          <ResponsiveContainer>
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
              <CartesianGrid vertical={false} stroke="var(--line)" />
              <XAxis
                dataKey="date"
                tickFormatter={fmtDay}
                interval={ticks - 1}
                tick={{ fill: "var(--ink-3)", fontSize: 11 }}
                axisLine={{ stroke: "var(--line)" }}
                tickLine={false}
                minTickGap={24}
              />
              <YAxis
                allowDecimals={false}
                tickFormatter={fmtCompact}
                tick={{ fill: "var(--ink-3)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={44}
              />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: "var(--ink-3)", strokeDasharray: "3 3" }} />
              {[...SERIES].reverse().map((s) => (
                <Line
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  name={s.label}
                  stroke={s.color}
                  strokeWidth={2}
                  strokeDasharray={s.dash}
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--card)" }}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="max-h-60 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-card text-left text-xs text-ink-3">
              <tr>
                <th className="py-1.5 font-medium">Date</th>
                <th className="py-1.5 text-right font-medium">Clicks</th>
                <th className="py-1.5 text-right font-medium">Unique visitors</th>
              </tr>
            </thead>
            <tbody className="tabular">
              {[...data].reverse().map((d) => (
                <tr key={d.date} className="border-t border-line">
                  <td className="py-1.5 text-ink-2">{fmtDay(d.date)}</td>
                  <td className="py-1.5 text-right text-ink">{fmtNumber(d.clicks)}</td>
                  <td className="py-1.5 text-right text-ink">{fmtNumber(d.visitors)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
