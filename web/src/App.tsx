import { useEffect, useState } from "react";

import { DashboardPage } from "./DashboardPage";
import { TransactionsPage } from "./TransactionsPage";

// shortcut: hash routing for two pages, switch to a router once pages need params
const PAGES = [
  { path: "#/", label: "Dashboard", element: <DashboardPage /> },
  { path: "#/transactions", label: "Transactions", element: <TransactionsPage /> },
];

function useHash() {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

export function App() {
  const hash = useHash();
  const page = PAGES.find((p) => p.path === hash) ?? PAGES[0];
  return (
    <>
      <nav className="topnav" aria-label="Main">
        <span className="brand">Sankash</span>
        {PAGES.map((p) => (
          <a key={p.path} href={p.path} aria-current={p === page ? "page" : undefined}>
            {p.label}
          </a>
        ))}
        <a className="legacy" href="http://localhost:3000/rules" title="Rules, categories, import, accounts and settings still live in the Reflex app (task reflex)">
          Rules, import & more ↗
        </a>
      </nav>
      {page.element}
    </>
  );
}
