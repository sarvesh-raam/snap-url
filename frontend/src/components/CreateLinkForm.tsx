import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Link2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { links, type Link } from "../api";
import { localInputToIso } from "../format";
import { CopyButton, ErrorNote } from "./ui";

export function CreateLinkForm() {
  const queryClient = useQueryClient();
  const [url, setUrl] = useState("");
  const [alias, setAlias] = useState("");
  const [title, setTitle] = useState("");
  const [expires, setExpires] = useState("");
  const [more, setMore] = useState(false);
  const [created, setCreated] = useState<Link | null>(null);

  const create = useMutation({
    mutationFn: links.create,
    onSuccess: (link) => {
      setCreated(link);
      setUrl("");
      setAlias("");
      setTitle("");
      setExpires("");
      queryClient.invalidateQueries({ queryKey: ["links"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate({
      url,
      alias: alias.trim() || undefined,
      title: title.trim() || undefined,
      expires_at: localInputToIso(expires),
    });
  };

  return (
    <section className="card p-4 sm:p-5">
      <form onSubmit={submit} className="space-y-3">
        <label htmlFor="url" className="text-sm font-semibold text-ink">
          Shorten a link
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <Link2 size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-3" />
            <input
              id="url"
              className="input pl-9"
              placeholder="https://example.com/a/very/long/link"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              autoComplete="off"
            />
          </div>
          <button className="btn btn-primary" disabled={create.isPending || !url.trim()}>
            {create.isPending ? "Shortening…" : "Shorten"}
          </button>
        </div>

        <button
          type="button"
          className="inline-flex items-center gap-1 text-xs font-medium text-ink-2 hover:text-ink"
          onClick={() => setMore((m) => !m)}
          aria-expanded={more}
        >
          <ChevronDown size={14} className={`transition-transform ${more ? "rotate-180" : ""}`} />
          Custom alias, title and expiry
        </button>

        {more && (
          <div className="grid gap-2 sm:grid-cols-3">
            <label className="space-y-1">
              <span className="text-xs text-ink-2">Custom alias</span>
              <input
                className="input font-mono"
                placeholder="spring-sale"
                value={alias}
                onChange={(e) => setAlias(e.target.value)}
                pattern="[A-Za-z0-9_\-]{3,32}"
                title="3–32 letters, digits, - or _"
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-ink-2">Title</span>
              <input className="input" placeholder="Spring campaign" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
            </label>
            <label className="space-y-1">
              <span className="text-xs text-ink-2">Expires</span>
              <input className="input" type="datetime-local" value={expires} onChange={(e) => setExpires(e.target.value)} />
            </label>
          </div>
        )}

        <ErrorNote error={create.error} />
      </form>

      {created && (
        <div className="mt-4 flex items-center gap-3 rounded-lg bg-accent-soft px-3 py-2">
          <div className="min-w-0 flex-1">
            <div className="text-xs text-ink-2">Your short link is ready</div>
            <a href={created.short_url} target="_blank" rel="noreferrer" className="truncate font-mono text-sm font-medium text-accent hover:underline">
              {created.short_url}
            </a>
          </div>
          <CopyButton text={created.short_url} />
        </div>
      )}
    </section>
  );
}
