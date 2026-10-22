import { useEffect, useState } from "react";
import CheckPage from "./pages/CheckPage";
import Landing from "./pages/Landing";
import ReportPage from "./pages/ReportPage";

export function navigate(path: string) {
  window.location.hash = path;
}

function useRoute(): string[] {
  const read = () => window.location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const on = () => {
      setRoute(read());
      window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export function Wordmark() {
  return (
    <a className="wordmark" href="#/" aria-label="Twice, home">
      <svg viewBox="0 0 26 26" aria-hidden="true">
        <g fill="none" strokeWidth="1.6">
          <circle cx="11" cy="11" r="7.2" stroke="currentColor" />
          <circle cx="15" cy="15" r="7.2" stroke="var(--signal)" />
          <path d="M11 1.5v5M11 15.5v5M1.5 11h5M15.5 11h5" stroke="currentColor" />
        </g>
      </svg>
      Twice
    </a>
  );
}

function ThemeToggle() {
  const [theme, setTheme] = useState(document.documentElement.dataset.theme ?? "light");
  const next = theme === "dark" ? "light" : "dark";
  const flip = () => {
    const root = document.documentElement;
    root.style.setProperty("transition", "none");
    root.dataset.theme = next;
    localStorage.setItem("twice-theme", next);
    setTheme(next);
    requestAnimationFrame(() => root.style.removeProperty("transition"));
  };
  return (
    <button className="icon-btn" onClick={flip} aria-label={`Switch to ${next === "dark" ? "darkroom" : "light table"} theme`}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
        {theme === "dark" ? (
          <>
            <circle cx="12" cy="12" r="4.5" />
            <path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8" />
          </>
        ) : (
          <path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" />
        )}
      </svg>
    </button>
  );
}

export function TopBar({ children }: { children?: React.ReactNode }) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const probe = document.createElement("div");
    probe.style.cssText = "position:absolute;top:0;height:8px;width:1px;pointer-events:none";
    document.body.prepend(probe);
    const io = new IntersectionObserver(([e]) => setScrolled(!e.isIntersecting));
    io.observe(probe);
    return () => {
      io.disconnect();
      probe.remove();
    };
  }, []);
  return (
    <header className="topbar" data-scrolled={scrolled}>
      <Wordmark />
      <nav>
        {children}
        <ThemeToggle />
      </nav>
    </header>
  );
}

export default function App() {
  const [page, id] = useRoute();
  if (page === "check" && id) return <CheckPage id={id} />;
  if (page === "report" && id) return <ReportPage id={id} />;
  return <Landing />;
}
