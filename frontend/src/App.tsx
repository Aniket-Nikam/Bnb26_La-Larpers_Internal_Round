import { lazy, Suspense } from "react";
import {
  BrowserRouter,
  Link,
  Outlet,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  FlaskConical,
  Globe2,
  LogOut,
  Plus,
  ShieldCheck,
  Ticket,
} from "lucide-react";
import {
  DiscoveryPage,
  DropDetail,
  FairnessPage,
  LandingPage,
  ProofPage,
  ReceiptPage,
  ReceiptsPage,
  RegisterPage,
  SignInPage,
} from "./pages/PublicPages";
import { OrganizerGuard } from "./components/State";
import { LoadingBlock } from "./components/Design";
import { useLogout, useSession } from "./lib/api/client";
import type { Schema } from "./lib/api/client";
import { ThemeProvider, ThemeToggle } from "./lib/theme";

const OrganizerDashboard = lazy(() =>
  import("./pages/OrganizerPages").then((module) => ({
    default: module.OrganizerDashboard,
  })),
);
const CreateDrop = lazy(() =>
  import("./pages/OrganizerPages").then((module) => ({
    default: module.CreateDrop,
  })),
);
const ManageDrop = lazy(() =>
  import("./pages/OrganizerPages").then((module) => ({
    default: module.ManageDrop,
  })),
);
const AttackLab = lazy(() =>
  import("./pages/OrganizerPages").then((module) => ({
    default: module.AttackLab,
  })),
);
const ProfilePage = lazy(() =>
  import("./pages/OrganizerPages").then((module) => ({
    default: module.ProfilePage,
  })),
);

function SystemState() {
  const health = useQuery({
    queryKey: ["public-health"],
    queryFn: async () => {
      const response = await fetch("/api/health/ready");
      return (await response.json()) as Schema["ReadyHealth"];
    },
    retry: false,
    refetchInterval: 30000,
  });
  const ready = health.data?.status === "ready";
  const label = health.isPending
    ? "Checking system"
    : ready
      ? "System ready"
      : health.data?.status === "degraded"
        ? "System protected"
        : "System unavailable";
  return (
    <span className="hidden items-center gap-2 text-xs font-semibold muted xl:inline-flex">
      <Activity className={"h-3.5 w-3.5 " + (ready ? "accent" : "")} />
      {label}
    </span>
  );
}

function AppShell() {
  const session = useSession();
  const logout = useLogout();
  const location = useLocation();
  const organizerAccount = ["organizer", "admin"].includes(
    session.data?.principal.role ?? "",
  );
  const navClass = (path: string) =>
    "inline-flex h-10 shrink-0 items-center gap-2 whitespace-nowrap rounded-full px-3 transition-colors " +
    (location.pathname === path
      ? "bg-[rgb(var(--line)/0.08)] text-[rgb(var(--ink))] font-bold"
      : "text-[rgb(var(--muted))] hover:bg-[rgb(var(--line)/0.05)] hover:text-[rgb(var(--ink))]");
  const publicLinks = (
    <>
      <Link className={navClass("/")} to="/">
        Overview
      </Link>
      <Link className={navClass("/drops")} to="/drops">
        Discovery
      </Link>
      <Link className={navClass("/fairness")} to="/fairness">
        Fairness
      </Link>
      <Link className={navClass("/organizer")} to="/organizer">
        Organizer
      </Link>
    </>
  );
  const organizerLinks = (
    <>
      <Link className={navClass("/organizer")} to="/organizer">
        Dashboard
      </Link>
      <Link className={navClass("/organizer/new")} to="/organizer/new">
        <Plus className="hidden h-4 w-4 lg:block" />
        New drop
      </Link>
      <Link className={navClass("/organizer/lab")} to="/organizer/lab">
        <FlaskConical className="hidden h-4 w-4 lg:block" />
        Attack lab
      </Link>
      <Link className={navClass("/")} to="/">
        <Globe2 className="hidden h-4 w-4 lg:block" />
        Public site
      </Link>
    </>
  );

  return (
    <div className="app-shell flex flex-col">
      <header className="sticky top-0 z-40 border-b border-[rgb(var(--line)/0.1)] bg-[rgb(var(--canvas)/0.9)] backdrop-blur-xl">
        <div className="page-wrap grid h-[72px] grid-cols-[auto_1fr_auto] items-center gap-3 lg:gap-5">
          <Link
            to={organizerAccount ? "/organizer" : "/"}
            className="flex shrink-0 items-center gap-3 text-base font-extrabold tracking-[-0.04em]"
            aria-label="FairDrop home"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[rgb(var(--accent))] text-white dark:text-[rgb(var(--canvas))] shadow-sm">
              <Ticket className="h-4 w-4" strokeWidth={2.4} />
            </span>
            <span>FairDrop</span>
            {organizerAccount && (
              <span className="hidden text-xs font-semibold tracking-normal muted xl:inline">
                Organizer
              </span>
            )}
          </Link>
          <nav
            className="hidden min-w-0 items-center justify-center gap-1 text-sm font-semibold md:flex"
            aria-label={
              organizerAccount ? "Organizer workspace" : "Primary navigation"
            }
          >
            {organizerAccount ? organizerLinks : publicLinks}
          </nav>
          <div className="flex shrink-0 items-center justify-end gap-1 sm:gap-2">
            <SystemState />
            <ThemeToggle />
            {session.data?.principal.role === "participant" && (
              <Link
                className="button-ghost hidden sm:inline-flex"
                to="/entries"
              >
                My tickets
              </Link>
            )}
            {session.data ? (
              <>
                <Link
                  className="button-secondary hidden max-w-[132px] px-4 sm:inline-flex xl:max-w-[220px]"
                  to="/profile"
                  title={session.data.principal.display_name}
                >
                  <span className="xl:hidden">Account</span>
                  <span className="hidden truncate xl:inline">
                    {session.data.principal.display_name}
                  </span>
                </Link>
                <button
                  className="button-ghost px-3"
                  aria-label="Sign out"
                  disabled={logout.isPending}
                  onClick={() => logout.mutate()}
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </>
            ) : (
              <Link className="button" to="/sign-in">
                Sign in
                <ArrowRight className="h-4 w-4" />
              </Link>
            )}
          </div>
        </div>
        <nav
          className="no-scrollbar page-wrap flex gap-1 overflow-x-auto border-t border-[rgb(var(--line)/0.08)] py-2 text-sm font-semibold md:hidden"
          aria-label="Mobile navigation"
        >
          {organizerAccount ? organizerLinks : publicLinks}
          {session.data?.principal.role === "participant" && (
            <>
              <Link className={navClass("/entries")} to="/entries">
                Receipts
              </Link>
              <Link className={navClass("/profile")} to="/profile">
                Profile
              </Link>
            </>
          )}
        </nav>
      </header>

      <main className="page-wrap flex-1 pb-24">
        <Outlet />
      </main>

      <footer className="border-t border-[rgb(var(--line)/0.1)]">
        <div className="page-wrap grid gap-8 py-10 md:grid-cols-[1.5fr_1fr_1fr]">
          <div className="max-w-md">
            <div className="flex items-center gap-2 font-bold">
              <ShieldCheck className="h-5 w-5 accent" />
              FairDrop
            </div>
            <p className="mt-3 text-sm leading-relaxed muted">
              One eligible identity, one durable entry, one independently
              verifiable draw.
            </p>
          </div>
          <div className="text-sm">
            <p className="font-semibold">
              {organizerAccount ? "Operate" : "Explore"}
            </p>
            {organizerAccount ? (
              <div className="mt-3 flex flex-col gap-2 muted">
                <Link to="/organizer">Control room</Link>
                <Link to="/organizer/new">Create drop</Link>
                <Link to="/organizer/lab">Attack lab</Link>
              </div>
            ) : (
              <div className="mt-3 flex flex-col gap-2 muted">
                <Link to="/drops">Live drops</Link>
                <Link to="/fairness">How fairness works</Link>
                <Link to="/entries">My receipts</Link>
              </div>
            )}
          </div>
          <div className="text-sm">
            <p className="font-semibold">Transparency</p>
            <p className="mt-3 leading-relaxed muted">
              Speed and retry volume never influence lottery rank. Identity
              limits remain explicit.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Suspense
        fallback={
          <div className="page-wrap py-24">
            <LoadingBlock label="Loading secure workspace" />
          </div>
        }
      >
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<LandingPage />} />
            <Route path="/drops" element={<DiscoveryPage />} />
            <Route path="/fairness" element={<FairnessPage />} />
            <Route path="/drops/:id" element={<DropDetail />} />
            <Route path="/sign-in" element={<SignInPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/entries" element={<ReceiptsPage />} />
            <Route path="/entries/:id" element={<ReceiptPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/drops/:id/proof" element={<ProofPage />} />
            <Route
              path="/organizer"
              element={
                <OrganizerGuard>
                  <OrganizerDashboard />
                </OrganizerGuard>
              }
            />
            <Route
              path="/organizer/new"
              element={
                <OrganizerGuard>
                  <CreateDrop />
                </OrganizerGuard>
              }
            />
            <Route
              path="/organizer/drops/:id"
              element={
                <OrganizerGuard>
                  <ManageDrop />
                </OrganizerGuard>
              }
            />
            <Route
              path="/organizer/lab"
              element={
                <OrganizerGuard>
                  <AttackLab />
                </OrganizerGuard>
              }
            />
            <Route
              path="*"
              element={
                <div className="py-24">
                  <p className="eyebrow">404</p>
                  <h1 className="page-title mt-4">
                    This ticket went elsewhere.
                  </h1>
                  <Link className="button mt-8" to="/">
                    Return home
                  </Link>
                </div>
              }
            />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
    </ThemeProvider>
  );
}
