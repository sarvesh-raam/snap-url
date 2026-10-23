import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { Logo, ThemeToggle } from "../components/Layout";
import { ErrorNote } from "../components/ui";

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const isLogin = mode === "login";

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await (isLogin ? login : register)(email, password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from ?? "/dashboard", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col">
      <header className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-4">
        <Logo />
        <ThemeToggle />
      </header>
      <main className="grid flex-1 place-items-center px-4 pb-16">
        <form onSubmit={submit} className="card w-full max-w-sm space-y-4 p-6">
          <div>
            <h1 className="text-lg font-semibold text-ink">{isLogin ? "Welcome back" : "Create your account"}</h1>
            <p className="mt-1 text-sm text-ink-3">
              {isLogin ? "Sign in to manage your links." : "Short links and click analytics, free."}
            </p>
          </div>
          <label className="block space-y-1">
            <span className="text-xs font-medium text-ink-2">Email</span>
            <input
              className="input"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="block space-y-1">
            <span className="text-xs font-medium text-ink-2">Password</span>
            <input
              className="input"
              type="password"
              autoComplete={isLogin ? "current-password" : "new-password"}
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {!isLogin && <span className="text-xs text-ink-3">At least 8 characters</span>}
          </label>
          <ErrorNote error={error} />
          <button className="btn btn-primary w-full" disabled={busy}>
            {busy ? "Please wait…" : isLogin ? "Sign in" : "Create account"}
          </button>
          <p className="text-center text-sm text-ink-3">
            {isLogin ? "New here? " : "Already have an account? "}
            <Link to={isLogin ? "/register" : "/login"} className="font-medium text-accent hover:underline">
              {isLogin ? "Create an account" : "Sign in"}
            </Link>
          </p>
        </form>
      </main>
    </div>
  );
}
