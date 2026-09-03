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

// Dev-only screenshot/render harness (never registered in production builds).
const ShotHarness = import.meta.env.DEV
  ? React.lazy(() => import("./pages/ShotHarness"))
  : null;

const router = createBrowserRouter([
  {
    path: "/",
    element: <UniversalRoot />
  },
  ...(import.meta.env.DEV && ShotHarness
    ? [{ path: "/__shot", element: <ShotHarness /> }]
    : []),
  {
    path: "/legacy",
    element: <EurekaShell />,
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

