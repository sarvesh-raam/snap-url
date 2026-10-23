import { useQuery } from "@tanstack/react-query";
import { links } from "../api";
import { ClicksChart } from "../components/ClicksChart";
import { CreateLinkForm } from "../components/CreateLinkForm";
import { LinksTable } from "../components/LinksTable";
import { Skeleton, StatTile } from "../components/ui";

export function Dashboard() {
  const overview = useQuery({ queryKey: ["overview"], queryFn: () => links.overview(30), refetchInterval: 15_000 });
  const o = overview.data;

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold tracking-tight text-ink">Dashboard</h1>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {o ? (
          <>
            <StatTile label="Total clicks" value={o.total_clicks} hint="All time, bots excluded" />
            <StatTile label="Last 7 days" value={o.clicks_last_7d} hint="Clicks" />
            <StatTile label="Links" value={o.total_links} />
            <StatTile label="Live links" value={o.active_links} hint="Turned on" />
          </>
        ) : (
          Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-[92px]" />)
        )}
      </div>
      <CreateLinkForm />
      {o ? <ClicksChart data={o.timeseries} title="Clicks across all links · last 30 days" /> : <Skeleton className="h-80" />}
      <LinksTable />
    </div>
  );
}
