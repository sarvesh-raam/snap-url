import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, ChevronLeft, ChevronRight, Power, QrCode, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { links, type Link } from "../api";
import { fmtNumber, fmtRelative, hostOf, isExpired } from "../format";
import { QrDialog } from "./QrDialog";
import { Badge, CopyButton, ErrorNote, Segmented, Skeleton } from "./ui";

const PAGE_SIZE = 10;

function useDebounced<T>(value: T, ms = 250) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function Status({ link }: { link: Link }) {
  if (!link.is_active) return <Badge tone="muted">Off</Badge>;
  if (isExpired(link)) return <Badge tone="critical">Expired</Badge>;
  return <Badge tone="good">Live</Badge>;
}

export function LinksTable() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<"recent" | "clicks">("recent");
  const [page, setPage] = useState(1);
  const [qrFor, setQrFor] = useState<Link | null>(null);
  const q = useDebounced(search.trim());

  useEffect(() => setPage(1), [q, sort]);

  const list = useQuery({
    queryKey: ["links", { q, sort, page }],
    queryFn: () => links.list({ q, sort, page, page_size: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["links"] });
    queryClient.invalidateQueries({ queryKey: ["overview"] });
  };
  const toggle = useMutation({
    mutationFn: (l: Link) => links.update(l.id, { is_active: !l.is_active }),
    onSuccess: refresh,
  });
  const remove = useMutation({ mutationFn: (l: Link) => links.remove(l.id), onSuccess: refresh });

  const data = list.data;
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <section className="card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-4">
        <h2 className="text-sm font-semibold text-ink">
          Your links {data && <span className="tabular font-normal text-ink-3">· {fmtNumber(data.total)}</span>}
        </h2>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <div className="relative flex-1 sm:w-60 sm:flex-none">
            <Search size={15} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-3" />
            <input
              className="input py-1.5 pl-8"
              placeholder="Search links"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search links"
            />
          </div>
          <Segmented
            label="Sort by"
            value={sort}
            onChange={setSort}
            options={[
              { value: "recent", label: "Recent" },
              { value: "clicks", label: "Top" },
            ]}
          />
        </div>
      </div>

      <ErrorNote error={list.error ?? toggle.error ?? remove.error} />

      {list.isLoading ? (
        <div className="space-y-3 p-4">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-10" />
          ))}
        </div>
      ) : data && data.items.length === 0 ? (
        <div className="px-4 py-14 text-center">
          <p className="text-sm font-medium text-ink">{q ? "No links match that search" : "No links yet"}</p>
          <p className="mt-1 text-sm text-ink-3">{q ? "Try another word." : "Shorten your first URL above."}</p>
        </div>
      ) : (
        <ul className="divide-y divide-line">
          {data?.items.map((l) => (
            <li key={l.id} className="flex items-center gap-3 px-4 py-3 hover:bg-sunken/50">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <RouterLink to={`/links/${l.id}`} className="min-w-0 truncate font-mono text-sm font-medium text-accent hover:underline">
                    {/* On phones the host is dropped so the code itself is never cut off. */}
                    <span className="hidden sm:inline">{l.short_url.replace(/^https?:\/\//, "").slice(0, -l.code.length)}</span>
                    <span className="sm:hidden">/</span>
                    {l.code}
                  </RouterLink>
                  <Status link={l} />
                </div>
                <div className="mt-0.5 truncate text-xs text-ink-3">
                  {l.title ? <span className="text-ink-2">{l.title} · </span> : null}
                  <span title={l.target_url}>{hostOf(l.target_url)}</span> · {fmtRelative(l.created_at)}
                </div>
              </div>
              <div className="hidden text-right sm:block">
                <div className="tabular text-sm font-semibold text-ink">{fmtNumber(l.click_count)}</div>
                <div className="text-xs text-ink-3">clicks</div>
              </div>
              <div className="flex items-center">
                <CopyButton text={l.short_url} />
                <button className="icon-btn" onClick={() => setQrFor(l)} aria-label="Show QR code" title="QR code">
                  <QrCode size={16} />
                </button>
                <RouterLink to={`/links/${l.id}`} className="icon-btn hidden sm:inline-grid" aria-label="Analytics" title="Analytics">
                  <BarChart3 size={16} />
                </RouterLink>
                <button
                  className="icon-btn hidden sm:inline-grid"
                  onClick={() => toggle.mutate(l)}
                  aria-label={l.is_active ? "Turn link off" : "Turn link on"}
                  title={l.is_active ? "Turn off" : "Turn on"}
                >
                  <Power size={16} />
                </button>
                <button
                  className="icon-btn hover:!text-critical"
                  onClick={() => window.confirm(`Delete ${l.short_url}? Its analytics are deleted too.`) && remove.mutate(l)}
                  aria-label="Delete link"
                  title="Delete"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {data && data.total > PAGE_SIZE && (
        <div className="flex items-center justify-between border-t border-line px-4 py-2.5 text-xs text-ink-3">
          <span className="tabular">
            Page {page} of {pages}
          </span>
          <div className="flex gap-1">
            <button className="icon-btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} aria-label="Previous page">
              <ChevronLeft size={16} />
            </button>
            <button className="icon-btn" disabled={page >= pages} onClick={() => setPage((p) => p + 1)} aria-label="Next page">
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {qrFor && <QrDialog link={qrFor} onClose={() => setQrFor(null)} />}
    </section>
  );
}
