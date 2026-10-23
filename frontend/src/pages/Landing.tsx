import { BarChart3, Globe2, MousePointerClick, QrCode, ShieldCheck, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { Logo, ThemeToggle } from "../components/Layout";

const FEATURES = [
  { icon: Zap, title: "Fast redirects", body: "Links resolve from a Redis cache; analytics are written off the request path." },
  { icon: Globe2, title: "Country, device, referrer", body: "See where clicks come from, on what device, and which site sent them." },
  { icon: ShieldCheck, title: "Private by design", body: "IP addresses are never stored. Visitors are counted with a daily-rotating hash." },
  { icon: BarChart3, title: "Bot filtering", body: "Crawlers and link previewers are flagged and kept out of your numbers." },
  { icon: QrCode, title: "QR codes", body: "Every link gets a downloadable QR code for print and slides." },
  { icon: MousePointerClick, title: "Custom aliases & expiry", body: "Pick a memorable alias, edit the destination later, or set links to expire." },
];

export function Landing() {
  const { user } = useAuth();
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Logo />
        <div className="flex items-center gap-1">
          <ThemeToggle />
          {user ? (
            <Link to="/dashboard" className="btn btn-primary">
              Dashboard
            </Link>
          ) : (
            <>
              <Link to="/login" className="btn btn-ghost">
                Sign in
              </Link>
              <Link to="/register" className="btn btn-primary">
                Get started
              </Link>
            </>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4">
        <section className="py-16 text-center sm:py-24">
          <h1 className="mx-auto max-w-2xl text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
            Short links that tell you who clicked
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-base text-ink-2 sm:text-lg">
            Shorten any URL, share it anywhere, and watch clicks arrive by country, device and referrer, live.
          </p>
          <div className="mt-8 flex justify-center gap-2">
            <Link to={user ? "/dashboard" : "/register"} className="btn btn-primary px-5 py-2.5">
              {user ? "Open dashboard" : "Create a free account"}
            </Link>
          </div>
        </section>

        <section className="grid gap-3 pb-20 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <div key={title} className="card p-5">
              <Icon size={20} className="text-accent" />
              <h2 className="mt-3 text-sm font-semibold text-ink">{title}</h2>
              <p className="mt-1 text-sm text-ink-2">{body}</p>
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}
