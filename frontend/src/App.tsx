import type { CSSProperties } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { LocaleProvider, useLocale } from "./shared/hooks/useLocale";
import { BoatApp } from "./boat/BoatApp";
import { ShoreConsole } from "./shore/ShoreConsole";
import { StudyRoutes } from "./study/StudyRoutes";

function TopNav() {
  const { t } = useLocale();
  const linkStyle = ({ isActive }: { isActive: boolean }): CSSProperties => ({
    padding: "var(--space-2) var(--space-4)",
    minHeight: "var(--touch-target)",
    display: "flex",
    alignItems: "center",
    color: isActive ? "var(--color-accent)" : "var(--color-text-muted)",
    borderBottom: isActive ? "2px solid var(--color-accent)" : "2px solid transparent",
    textDecoration: "none",
    fontWeight: isActive ? 700 : 400,
  });

  return (
    <nav
      style={{
        display: "flex",
        justifyContent: "center",
        gap: "var(--space-2)",
        borderBottom: "1px solid var(--color-border)",
        background: "var(--color-surface)",
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}
    >
      <NavLink to="/" end style={linkStyle}>
        {t("boatTab")}
      </NavLink>
      <NavLink to="/shore" style={linkStyle}>
        {t("shoreTab")}
      </NavLink>
      <NavLink to="/study" style={linkStyle}>
        {t("studyTab")}
      </NavLink>
    </nav>
  );
}

function App() {
  return (
    <LocaleProvider>
      <TopNav />
      <Routes>
        <Route path="/" element={<BoatApp />} />
        <Route path="/shore" element={<ShoreConsole />} />
        <Route path="/study" element={<StudyRoutes />} />
      </Routes>
    </LocaleProvider>
  );
}

export default App;
