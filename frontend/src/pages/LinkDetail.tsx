import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, Pencil, QrCode } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";
import { ApiError, links, type Link } from "../api";
import { BarList } from "../components/BarList";
import { ClicksChart } from "../components/ClicksChart";
import { Status } from "../components/LinksTable";
import { QrDialog } from "../components/QrDialog";
import { CopyButton, ErrorNote, Segmented, Skeleton, StatTile } from "../components/ui";
import { countryFlag, countryName, fmtDate, isoToLocalInput, localInputToIso } from "../format";

const RANGES = [
  { value: 7, label: "7d" },
  { value: 30, label: "30d" },
  { value: 90, label: "90d" },
];

const DEVICE_LABELS: Record<string, string> = { desktop: "Desktop", mobile: "Mobile", tablet: "Tablet", other: "Other" };

function EditForm({ link, onDone }: { link: Link; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [url, setUrl] = useState(link.target_url);
  const [title, setTitle] = useState(link.title ?? "");
  const [expires, setExpires] = useState(isoToLocalInput(link.expires_at));
  const [active, setActive] = useState(link.is_active);

  const save = useMutation({
    mutationFn: () =>
      links.update(link.id, {
        url,
        title: title.trim() || null,
        expires_at: localInputToIso(expires),
        is_active: active,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["link", link.id], updated);
      queryClient.invalidateQueries({ queryKey: ["links"] });
      onDone();
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };

  return (
    <form onSubmit={submit} className="card space-y-3 p-4 sm:p-5">
      <label className="block space-y-1">
        <span className="text-xs text-ink-2">Destination URL</span>
        <input className="input" value={url} onChange={(e) => setUrl(e.target.value)} required />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block space-y-1">
          <span className="text-xs text-ink-2">Title</span>
          <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
        </label>
        <label className="block space-y-1">
          <span className="text-xs text-ink-2">Expires (leave empty for never)</span>
          <input className="input" type="datetime-local" value={expires} onChange={(e) => setExpires(e.target.value)} />
        </label>
      </div>
      <label className="flex items-center gap-2 text-sm text-ink">
        <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} className="h-4 w-4 accent-[var(--accent)]" />
        Link is on (visitors are redirected)
      </label>
      <ErrorNote error={save.error} />
      <div className="flex gap-2">
        <button className="btn btn-primary" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save changes"}
        </button>
        <button type="button" className="btn btn-ghost" onClick={onDone}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export function LinkDetail() {
  const id = Number(useParams().id);
  const [days, setDays] = useState(30);
  const [editing, setEditing] = useState(false);
  const [qr, setQr] = useState(false);

  const link = useQuery({ queryKey: ["link", id], queryFn: () => links.get(id), retry: false });
  const stats = useQuery({
    queryKey: ["stats", id, days],
    queryFn: () => links.stats(id, days),
    enabled: link.isSuccess,
    refetchInterval: 10_000,
  });

  if (link.error instanceof ApiError && link.error.status === 404) {
    return (
      <div className="py-20 text-center">
        <p className="font-medium text-ink">Link not found</p>
        <RouterLink to="/dashboard" className="mt-2 inline-block text-sm text-accent hover:underline">
          Back to dashboard
        </RouterLink>
      </div>
    );
  }

  const l = link.data;
  const s = stats.data;

  return (
    <div className="space-y-5">
      <RouterLink to="/dashboard" className="-ml-1 inline-flex items-center gap-1 rounded-md px-1 py-1.5 text-sm text-ink-2 hover:text-ink">
        <ArrowLeft size={15} /> All links
      </RouterLink>

      {l ? (
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="min-w-0 break-all font-mono text-lg font-semibold text-ink sm:text-xl">
                {l.short_url.replace(/^https?:\/\//, "")}
              </h1>
              <CopyButton text={l.short_url} />
              <Status link={l} />
            </div>
            {l.title && <p className="mt-0.5 text-sm text-ink">{l.title}</p>}
            <a
              href={l.target_url}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-flex max-w-full items-center gap-1 text-sm text-ink-3 hover:text-ink"
            >
              <span className="truncate">{l.target_url}</span>
              <ExternalLink size={13} className="shrink-0" />
            </a>
            <p className="mt-1 text-xs text-ink-3">
              Created {fmtDate(l.created_at)}
              {l.expires_at && ` · Expires ${fmtDate(l.expires_at)}`}
            </p>
          </div>
          <div className="flex gap-2">
            <button className="btn btn-outline" onClick={() => setQr(true)}>
              <QrCode size={15} /> QR
            </button>
            <button className="btn btn-outline" onClick={() => setEditing((e) => !e)}>
              <Pencil size={15} /> Edit
            </button>
          </div>
        </header>
      ) : (
        <Skeleton className="h-20" />
      )}

      {l && editing && <EditForm link={l} onDone={() => setEditing(false)} />}

      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink">Analytics</h2>
        <Segmented label="Date range" value={days} onChange={setDays} options={RANGES} />
      </div>
      <ErrorNote error={stats.error} />

      {s ? (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <StatTile label="Clicks" value={s.total_clicks} hint={`Last ${days} days`} />
            <StatTile label="Unique visitors" value={s.unique_visitors} hint="Counted per day" />
            <div className="col-span-2 sm:col-span-1">
              <StatTile label="Bot clicks" value={s.bot_clicks} hint="Filtered from all charts" />
            </div>
          </div>
          <ClicksChart data={s.timeseries} />
          <div className="grid gap-3 md:grid-cols-2">
            <BarList
              title="Countries"
              rows={s.countries}
              renderKey={(k) =>
                k === "Unknown" ? (
                  "Unknown"
                ) : (
                  <>
                    <span aria-hidden className="mr-1.5">
                      {countryFlag(k)}
                    </span>
                    {countryName(k)}
                  </>
                )
              }
            />
            <BarList title="Referrers" rows={s.referrers} />
            <BarList title="Devices" rows={s.devices} renderKey={(k) => DEVICE_LABELS[k] ?? k} />
            <BarList title="Browsers" rows={s.browsers} />
            <BarList title="Operating systems" rows={s.os} />
          </div>
        </>
      ) : (
        <div className="space-y-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-80" />
        </div>
      )}

      {qr && l && <QrDialog link={l} onClose={() => setQr(false)} />}
    </div>
  );
}
