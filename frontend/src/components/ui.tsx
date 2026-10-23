import { Check, Copy } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { fmtNumber } from "../format";

export function StatTile({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-ink-3">{label}</div>
      <div className="tabular mt-1.5 text-2xl font-semibold text-ink">{fmtNumber(value)}</div>
      {hint && <div className="mt-0.5 text-xs text-ink-3">{hint}</div>}
    </div>
  );
}

export function CopyButton({ text, label = "Copy short link" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number>();
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      return;
    }
    setCopied(true);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button className="icon-btn" onClick={copy} aria-label={label} title={copied ? "Copied" : label}>
      {copied ? <Check size={16} className="text-good" /> : <Copy size={16} />}
    </button>
  );
}

export function Badge({ tone, children }: { tone: "good" | "muted" | "critical"; children: ReactNode }) {
  const cls = {
    good: "text-good",
    muted: "text-ink-3",
    critical: "text-critical",
  }[tone];
  const dot = { good: "bg-good", muted: "bg-ink-3", critical: "bg-critical" }[tone];
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} aria-hidden />
      {children}
    </span>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <p role="alert" className="text-sm text-critical">
      {error instanceof Error ? error.message : "Something went wrong"}
    </p>
  );
}

export function Segmented<T extends string | number>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div role="group" aria-label={label} className="inline-flex rounded-lg border border-line bg-card p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          aria-pressed={o.value === value}
          className={`min-h-8 rounded-md px-3 py-1 text-xs font-medium sm:min-h-0 ${
            o.value === value ? "bg-sunken text-ink" : "text-ink-3 hover:text-ink"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-sunken ${className}`} />;
}
