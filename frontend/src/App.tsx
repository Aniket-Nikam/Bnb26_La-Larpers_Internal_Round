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
  LogOut,
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
  const isOrganizer = location.pathname.startsWith("/organizer");
  const active = (path: string) =>
    location.pathname === path
      ? "text-[rgb(var(--ink))]"
      : "text-[rgb(var(--muted))] hover:text-[rgb(var(--ink))]";
  const publicLinks = (
    <>
      <Link className={active("/")} to="/">
        Overview
      </Link>
      <Link className={active("/drops")} to="/drops">
        Discovery
      </Link>
      <Link className={active("/fairness")} to="/fairness">
        Fairness
      </Link>
      <Link className={active("/organizer")} to="/organizer">
        Organizer
      </Link>
    </>
  );
  const organizerLinks = (
    <>
      <Link className={active("/organizer")} to="/organizer">
        Dashboard
      </Link>
      <Link className={active("/organizer/lab")} to="/organizer/lab">
        <FlaskConical className="h-4 w-4" />
        Lab
      </Link>
      <Link className={active("/")} to="/">
        Exit
      </Link>
    </>
  );

  return (
    <div className="app-shell flex flex-col">
      <header className="sticky top-0 z-40 border-b border-white/[0.07] bg-[rgb(var(--canvas)/0.9)] backdrop-blur-xl">
        <div className="page-wrap flex h-[72px] items-center justify-between gap-5">
          <Link
            to="/"
            className="flex shrink-0 items-center gap-3 text-base font-extrabold tracking-[-0.04em]"
            aria-label="FairDrop home"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[rgb(var(--accent))] text-[rgb(var(--canvas))]">
              <Ticket className="h-4 w-4" strokeWidth={2.4} />
            </span>
            <span>FairDrop</span>
            {isOrganizer && (
              <span className="hidden text-xs font-semibold tracking-normal muted sm:inline">
                Organizer
              </span>
            )}
          </Link>
          <nav className="hidden items-center gap-6 text-sm font-semibold lg:flex">
            {isOrganizer ? organizerLinks : publicLinks}
          </nav>
          <div className="flex items-center gap-3">
            <SystemState />
            {!isOrganizer && session.data && (
              <Link
                className="button-ghost hidden sm:inline-flex"
                to="/entries"
              >
                My tickets
              </Link>
            )}
            {!isOrganizer && session.data ? (
              <>
                <Link
                  className="button-secondary hidden sm:inline-flex"
                  to="/profile"
                >
                  {session.data.principal.display_name}
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
            ) : !isOrganizer ? (
              <Link className="button" to="/sign-in">
                Sign in
                <ArrowRight className="h-4 w-4" />
              </Link>
            ) : null}
          </div>
        </div>
        <nav className="no-scrollbar page-wrap flex gap-5 overflow-x-auto pb-3 text-sm font-semibold lg:hidden">
          {isOrganizer ? organizerLinks : publicLinks}
          {!isOrganizer && session.data && (
            <>
              <Link className={active("/entries")} to="/entries">
                Receipts
              </Link>
              <Link className={active("/profile")} to="/profile">
                Profile
              </Link>
            </>
          )}
        </nav>
      </header>

      <main className="page-wrap flex-1 pb-24">
        <Outlet />
      </main>

      <footer className="border-t border-white/[0.07]">
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
            <p className="font-semibold">Explore</p>
            <div className="mt-3 flex flex-col gap-2 muted">
              <Link to="/drops">Live drops</Link>
              <Link to="/fairness">How fairness works</Link>
              <Link to="/entries">My receipts</Link>
            </div>
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
  );
}
