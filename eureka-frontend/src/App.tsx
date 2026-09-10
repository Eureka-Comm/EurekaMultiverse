import React from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { EurekaShell } from "./components/layout/EurekaShell";
import Overview from "./pages/Overview";
import CasesList from "./pages/Cases/CasesList";
import CaseDetail from "./pages/Cases/CaseDetail";
import Chat from "./pages/Cognitive/Chat";
import Sandbox from "./pages/Cognitive/Sandbox";
import Files from "./pages/Workspace/Files";
import Data from "./pages/Workspace/Data";
import Dashboard from "./pages/Analytics/Dashboard";
import Explorer from "./pages/Analytics/Explorer";
import Scenarios from "./pages/Analytics/Scenarios";
import Networks from "./pages/Analytics/Networks";
import Objective from "./pages/Decision/Objective";
import Predicate from "./pages/Decision/Predicate";
import Evaluations from "./pages/Decision/Evaluations";
import Ranking from "./pages/Decision/Ranking";
import Selection from "./pages/Decision/Selection";
import Prescription from "./pages/Decision/Prescription";
import Authority from "./pages/Governance/Authority";
import Freezer from "./pages/Governance/Freezer";
import Unfreezer from "./pages/Governance/Unfreezer";
import Actioner from "./pages/Governance/Actioner";
import Executive from "./pages/Story/Executive";
import Technical from "./pages/Story/Technical";
import Timeline from "./pages/Story/Timeline";
import Agents from "./pages/System/Agents";
import Runtime from "./pages/System/Runtime";
import Audit from "./pages/System/Audit";
import Settings from "./pages/System/Settings";

import UniversalRoot from "./pages/UniversalRoot";
import RequireAuth from "./components/auth/RequireAuth";
import { LoginPage, RegisterPage, ForgotPasswordPage, ResetPasswordPage } from "./pages/auth/AuthPages";
import AdminConsole from "./pages/admin/AdminConsole";
import AdminLayout from "./pages/admin/AdminLayout";

// Dev-only screenshot/render harness (never registered in production builds).
const ShotHarness = import.meta.env.DEV
  ? React.lazy(() => import("./pages/ShotHarness"))
  : null;
const CoreConstellationDemo = import.meta.env.DEV
  ? React.lazy(() => import("./pages/CoreConstellationDemo"))
  : null;
const CognitiveFieldDemo = import.meta.env.DEV
  ? React.lazy(() => import("./pages/CognitiveFieldDemo"))
  : null;
const WhatIfDemo = import.meta.env.DEV
  ? React.lazy(() => import("./pages/WhatIfDemo"))
  : null;
const AuditDemo = import.meta.env.DEV
  ? React.lazy(() => import("./pages/AuditDemo"))
  : null;
const WorkAuditDemo = import.meta.env.DEV
  ? React.lazy(() => import("./pages/WorkAuditDemo"))
  : null;
const ObservabilityConsoleDemo = import.meta.env.DEV
  ? React.lazy(() => import("./pages/ObservabilityConsoleDemo"))
  : null;

// Productive observability entry (available in production builds, not DEV-gated).
const ObservabilityEntry = React.lazy(() => import("./pages/ObservabilityEntry"));

const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    path: "/forgot-password",
    element: <ForgotPasswordPage />,
  },
  {
    path: "/reset-password",
    element: <ResetPasswordPage />,
  },
  {
    path: "/admin",
    element: <RequireAuth requireAdmin><AdminLayout><AdminConsole /></AdminLayout></RequireAuth>,
  },
  {
    path: "/",
    element: <RequireAuth><UniversalRoot /></RequireAuth>
  },
  ...(import.meta.env.DEV && ShotHarness
    ? [{ path: "/__shot", element: <ShotHarness /> }]
    : []),
  ...(import.meta.env.DEV && CoreConstellationDemo
    ? [{ path: "/__constellation", element: <CoreConstellationDemo /> }]
    : []),
  ...(import.meta.env.DEV && CognitiveFieldDemo
    ? [{ path: "/__field", element: <CognitiveFieldDemo /> }]
    : []),
  ...(import.meta.env.DEV && WhatIfDemo
    ? [{ path: "/__whatif", element: <WhatIfDemo /> }]
    : []),
  ...(import.meta.env.DEV && AuditDemo
    ? [{ path: "/__audit", element: <AuditDemo /> }]
    : []),
  ...(import.meta.env.DEV && WorkAuditDemo
    ? [{ path: "/__workaudit", element: <WorkAuditDemo /> }]
    : []),
  ...(import.meta.env.DEV && ObservabilityConsoleDemo
    ? [{ path: "/__obs", element: <ObservabilityConsoleDemo /> }]
    : []),
  {
    path: "/observability",
    element: <RequireAuth><React.Suspense fallback={<div className="p-6 text-[var(--eureka-text-label)]">Loading observability…</div>}><ObservabilityEntry /></React.Suspense></RequireAuth>,
  },
  {
    path: "/legacy",
    element: <RequireAuth><EurekaShell /></RequireAuth>,
    children: [
      { path: "", element: <Overview /> },
      { path: "cases", element: <CasesList /> },
      { path: "cases/:id", element: <CaseDetail /> },
      { path: "files", element: <Files /> },
      { path: "data", element: <Data /> },
      { path: "chat", element: <Chat /> },
      { path: "sandbox", element: <Sandbox /> },
      { path: "analytics", element: <Dashboard /> },
      { path: "analytics/explorer", element: <Explorer /> },
      { path: "analytics/scenarios", element: <Scenarios /> },
      { path: "analytics/networks", element: <Networks /> },
      { path: "decision/objective", element: <Objective /> },
      { path: "decision/predicate", element: <Predicate /> },
      { path: "decision/evaluations", element: <Evaluations /> },
      { path: "decision/ranking", element: <Ranking /> },
      { path: "decision/selection", element: <Selection /> },
      { path: "decision/prescription", element: <Prescription /> },
      { path: "governance/authority", element: <Authority /> },
      { path: "governance/freezer", element: <Freezer /> },
      { path: "governance/unfreezer", element: <Unfreezer /> },
      { path: "governance/actioner", element: <Actioner /> },
      { path: "story/executive", element: <Executive /> },
      { path: "story/technical", element: <Technical /> },
      { path: "story/timeline", element: <Timeline /> },
      { path: "agents", element: <Agents /> },
      { path: "runtime", element: <Runtime /> },
      { path: "audit", element: <Audit /> },
      { path: "settings", element: <Settings /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}

