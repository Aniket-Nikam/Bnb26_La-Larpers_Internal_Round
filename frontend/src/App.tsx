import {
  BrowserRouter,
  Routes,
  Route,
  Outlet,
  Link,
  useLocation,
} from "react-router-dom";
import { Ticket, ArrowRight, ShieldAlert } from "lucide-react";
import {
  LandingPage,
  DropDetail,
  SignInPage,
  ReceiptsPage,
  ReceiptPage,
  ProofPage,
} from "./pages/PublicPages";
import {
  OrganizerDashboard,
  AttackLab,
  CreateDrop,
  ManageDrop,
  ProfilePage,
} from "./pages/OrganizerPages";

import { OrganizerGuard } from "./components/State";
import { useSession, useLogout } from "./lib/api/client";

function AppShell() {
  const session = useSession();
  const logout = useLogout();
  const location = useLocation();
  const isOrganizer = location.pathname.startsWith("/organizer");

  return (
    <div className="min-h-screen flex flex-col bg-black text-white font-sans selection:bg-white/30 selection:text-black">
      <header className="sticky top-0 z-50 bg-black py-6">
        <div className="max-w-5xl mx-auto px-6 flex items-center justify-between">
          <Link
            to="/"
            className="font-bold text-xl flex items-center gap-2 tracking-tighter text-white"
          >
            <div className="w-8 h-8 bg-white text-black rounded-full flex items-center justify-center">
              <Ticket className="w-4 h-4" strokeWidth={3} />
            </div>
            <span>
              FAIRDROP{" "}
              {isOrganizer && <span className="text-white/40">ORGANIZER</span>}
            </span>
          </Link>
          <nav className="flex flex-wrap items-center justify-end gap-3 md:gap-6 text-[13px] font-semibold text-white/40 tracking-widest uppercase">
            {!isOrganizer ? (
              <>
                <Link
                  to="/"
                  className={`hover:text-white transition-colors ${location.pathname === "/" ? "text-white" : ""}`}
                >
                  Overview
                </Link>
                <Link
                  to="/drops"
                  className={`hover:text-white transition-colors ${location.pathname === "/drops" ? "text-white" : ""}`}
                >
                  Discovery
                </Link>
                <Link
                  to="/organizer"
                  className="hover:text-white transition-colors"
                >
                  Organizer
                </Link>
                {session.data ? (
                  <>
                    <Link to="/entries">Receipts</Link>
                    <Link to="/profile">Profile</Link>
                    <button
                      disabled={logout.isPending}
                      onClick={() => logout.mutate()}
                    >
                      Sign out
                    </button>
                  </>
                ) : (
                  <Link
                    to="/sign-in"
                    className="flex items-center gap-2 hover:text-white transition-colors text-white border border-white/20 px-4 py-2 rounded-full"
                  >
                    Sign In <ArrowRight className="w-3 h-3" />
                  </Link>
                )}
              </>
            ) : (
              <>
                <Link
                  to="/organizer"
                  className={`hover:text-white transition-colors ${location.pathname === "/organizer" ? "text-white" : ""}`}
                >
                  Dashboard
                </Link>
                <Link
                  to="/organizer/lab"
                  className={`flex items-center gap-2 hover:text-white transition-colors ${location.pathname === "/organizer/lab" ? "text-white" : ""}`}
                >
                  <ShieldAlert className="w-4 h-4" /> Lab
                </Link>
                <Link to="/" className="hover:text-white transition-colors">
                  Exit
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      <main className="flex-1 w-full max-w-5xl mx-auto px-6 pb-24">
        <Outlet />
      </main>
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/drops" element={<LandingPage />} />
          <Route path="/drops/:id" element={<DropDetail />} />
          <Route path="/sign-in" element={<SignInPage />} />
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
              <p>
                Page not found. <Link to="/">Return home</Link>
              </p>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
