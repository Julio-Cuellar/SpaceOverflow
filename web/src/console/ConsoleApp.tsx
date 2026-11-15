import { useEffect, useMemo, useState } from "react";
import type { AppProps } from "../App";
import { useMission } from "./data/useMission";
import { voiceService } from "./data/voice";
import type { Mode } from "./model";
import { Overview } from "./pages/Overview";
import { Habitat } from "./pages/Habitat";
import { GroundPage } from "./pages/Ground";
import { Personal } from "./pages/Personal";
import { Settings } from "./pages/Settings";
import { Agent } from "./ui/Agent";
import { TaskPanel } from "./ui/Tasks";
import { CrewCard, Empty, Heading, Metric, Panel } from "./ui/Common";
const routes = [
  ["/", "⌂", "Mission overview", "overview"],
  ["/crew", "♙", "Crew health", "crew"],
  ["/habitat", "⌘", "Ship environment", "habitat"],
  ["/tasks", "☷", "Crew tasks", "tasks"],
  ["/assistant", "✳", "Health assistant", "assistant"],
  ["/ground", "⌁", "Ground control", "ground"],
  ["/settings", "⚙", "Settings", "settings"],
] as const;
export interface ConsoleProps {
  initialPath?: string;
  initialMode?: Mode;
  askAssistant?: AppProps["askAssistant"];
  speak?: AppProps["speak"];
}
export function ConsoleApp({
  initialPath = location.pathname,
  initialMode,
  askAssistant,
  speak,
}: ConsoleProps) {
  const [path, setPath] = useState(initialPath.replace(/\/$/, "") || "/");
  const [mode, setMode] = useState<Mode>(
    initialMode ??
      (import.meta.env.VITE_DATA_MODE === "backend" ? "backend" : "demo"),
  );
  const [menu, setMenu] = useState(false);
  const [personalSection, setPersonalSection] = useState("day");
  const [selectedCrew, setSelectedCrew] = useState("");
  const personal = path === "/dashboard-tripulation";
  const route = routes.find((r) => r[0] === path);
  const view = route?.[3] ?? "overview";
  const mission = useMission(mode, personal, view);
  const voice = useMemo(
    () =>
      import.meta.env.VITE_VOICE_URL
        ? voiceService(import.meta.env.VITE_VOICE_URL)
        : undefined,
    [],
  );
  useEffect(() => {
    const onPop = () => {
      setPath(location.pathname.replace(/\/$/, "") || "/");
      setMenu(false);
    };
    addEventListener("popstate", onPop);
    return () => removeEventListener("popstate", onPop);
  }, []);
  useEffect(() => {
    document.title = `Odyssey · ${personal ? "My crew workspace" : (route?.[2] ?? "Page not found")}`;
  }, [personal, route]);
  const navigate = (e: React.MouseEvent<HTMLAnchorElement>, target: string) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    history.pushState(null, "", target);
    setPath(target);
    setMenu(false);
    window.scrollTo({ top: 0 });
  };
  const person =
    mission.data.crew.find((p) => p.id === selectedCrew) ??
    mission.data.crew[0];
  const resources = Object.entries(mission.errors).filter(
    ([, message]) => message,
  );
  const title = personal
    ? "MY CREW WORKSPACE"
    : (route?.[2] ?? "PAGE NOT FOUND");
  const navigation = (
    <nav className="mission-nav" aria-label="Mission navigation">
      {routes.map(([href, icon, text]) => (
        <a
          key={href}
          href={href}
          onClick={(e) => navigate(e, href)}
          aria-current={path === href ? "page" : undefined}
        >
          <span aria-hidden="true">{icon}</span>
          {text}
        </a>
      ))}
    </nav>
  );
  return (
    <div className={`odyssey ${personal ? "personal-shell" : ""}`}>
      <a className="skip-link" href="#mission-content">
        Skip to content
      </a>
      {!personal && (
        <aside className={`mission-sidebar ${menu ? "open" : ""}`}>
          <a className="brand" href="/" onClick={(e) => navigate(e, "/")}>
            <span className="brand-mark">O</span>
            <span>
              <b>ODYSSEY</b>
              <small>CREW HEALTH SYSTEM</small>
            </span>
          </a>
          <span className="nav-label">MISSION CONTROL</span>
          {navigation}
          <div className="sidebar-bottom">
            <div className="mission-state">
              <i className="dot online" />
              <div>
                <b>Mission operations</b>
                <small>
                  {mode === "demo"
                    ? "Fictional review session"
                    : "Backend data adapter"}
                </small>
              </div>
            </div>
            <p className="sidebar-note">DECISION SUPPORT PROTOTYPE</p>
          </div>
        </aside>
      )}
      <div className="mission-main">
        <header className="mission-topbar">
          {personal ? (
            <>
              <a
                className="brand"
                href="/dashboard-tripulation"
                onClick={(e) => navigate(e, "/dashboard-tripulation")}
              >
                <span className="brand-mark">O</span>
                <span>
                  <b>ODYSSEY</b>
                  <small>MY CREW WORKSPACE</small>
                </span>
              </a>
              <nav className="personal-nav" aria-label="Personal sections">
                {[
                  ["day", "My day"],
                  ["habitat", "My habitat"],
                  ["routine", "My routine"],
                ].map(([key, text]) => (
                  <button
                    key={key}
                    aria-pressed={personalSection === key}
                    onClick={() => setPersonalSection(key)}
                  >
                    {text}
                  </button>
                ))}
              </nav>
            </>
          ) : (
            <>
              <button
                className="menu-button"
                aria-label="Toggle navigation"
                aria-expanded={menu}
                onClick={() => setMenu(!menu)}
              >
                ☰
              </button>
              <div className="breadcrumb">
                ODYSSEY / <b>{title}</b>
              </div>
            </>
          )}
          <div className="topbar-actions">
            <span className="connection">
              <i
                className={`dot ${mission.connection === "Connected" || mode === "demo" ? "online" : ""}`}
              />
              {mission.connection}
            </span>
            <label className="data-mode">
              Data source
              <select
                aria-label="Data source"
                value={mode}
                onChange={(e) => setMode(e.target.value as Mode)}
              >
                <option value="demo">Demo</option>
                <option value="backend">Backend</option>
              </select>
            </label>
            <span className="identity">
              <b>
                {personal
                  ? (mission.data.session?.crewMember.name ?? "Session pending")
                  : "Mission control"}
              </b>
              <small>
                {personal
                  ? mode === "demo"
                    ? "Demo session"
                    : "Current session"
                  : "Operations workspace"}
              </small>
            </span>
          </div>
        </header>
        <main id="mission-content" className="mission-content">
          <div className="prototype-notice">
            <span className="evidence">◇ PROTOTYPE</span>
            <span>Decision support prototype · Not a medical device</span>
            <span className="notice-origin">
              {mode === "demo"
                ? "All readings are simulated demo data"
                : "Backend adapter · Every reading retains its source label"}
            </span>
          </div>
          {resources.length > 0 && (
            <section
              className="connection-errors"
              aria-label="Data availability"
            >
              <h2>Some services are unavailable</h2>
              {resources.map(([resource, error]) => (
                <p key={resource}>
                  <b>
                    {resource === "session"
                      ? "Personal session"
                      : resource === "overview"
                        ? "Mission overview"
                        : resource === "ship"
                          ? "Habitat"
                          : resource === "ground"
                            ? "Ground control"
                            : resource === "rules"
                              ? "Rule catalog"
                              : "Tasks"}
                    :
                  </b>{" "}
                  {error}
                </p>
              ))}
              <p>
                Previously loaded data may be stale. Successful changes require
                backend confirmation.
              </p>
              <button className="button" onClick={mission.reload}>
                Retry services
              </button>
            </section>
          )}
          {Object.values(mission.states).includes("loading") && (
            <p className="loading-state" role="status">
              Loading workspace data…
            </p>
          )}
          {personal ? (
            <Personal mission={mission} section={personalSection} />
          ) : !route ? (
            <>
              <Heading
                eyebrow="ODYSSEY"
                title="Page not found"
                subtitle="This workspace route does not exist."
              />
              <a className="button" href="/" onClick={(e) => navigate(e, "/")}>
                Return to mission overview
              </a>
            </>
          ) : view === "overview" ? (
            <Overview mission={mission} />
          ) : view === "habitat" ? (
            <Habitat mission={mission} />
          ) : view === "ground" ? (
            <GroundPage mission={mission} />
          ) : view === "tasks" ? (
            <>
              <Heading
                eyebrow="CREW OPERATIONS"
                title="Crew tasks"
                subtitle="Daily activities, health routines and incident follow-up."
              />
              {mission.data.groundPlan && (
                <p className="inline-notice">
                  Ground plan v{mission.data.groundPlan.version} applied
                  {mission.data.groundPlan.rejected.length
                    ? ` · ${mission.data.groundPlan.rejected.length} rejected items`
                    : ""}
                </p>
              )}
              <TaskPanel
                tasks={mission.data.tasks}
                zones={mission.data.ship?.zones ?? []}
                run={mission.run}
                pending={mission.pending}
              />
              <Panel
                title="Health routine progress"
                subtitle="Critical alerts and ground tasks are not rewarded"
              >
                <p>
                  {mission.data.streak === null
                    ? "Progress unavailable"
                    : `${mission.data.streak} eligible health routines completed today`}
                </p>
              </Panel>
            </>
          ) : view === "crew" ? (
            <>
              <Heading
                eyebrow="CREW MONITORING"
                title="Crew health"
                subtitle="Authorized individual profiles and personal measurements."
              />
              {person ? (
                <>
                  <div
                    className="crew-selector"
                    aria-label="Select crew profile"
                  >
                    {mission.data.crew.map((p) => (
                      <button
                        className="button"
                        key={p.id}
                        aria-pressed={person.id === p.id}
                        onClick={() => setSelectedCrew(p.id)}
                      >
                        {p.name}
                      </button>
                    ))}
                  </div>
                  <div className="crew-detail">
                    <CrewCard person={person} />
                    <Panel
                      title={`${person.name} · Personal readings`}
                      subtitle="Illustrative crew fixture · not habitat sensors"
                    >
                      <div className="metric-grid">
                        {person.vitals.map((v) => (
                          <Metric key={v.key} vital={v} />
                        ))}
                      </div>
                      <p className="muted">
                        Personal trends and baselines require the crew service.
                      </p>
                    </Panel>
                  </div>
                </>
              ) : (
                <Empty>
                  Authorized crew profiles are not provided by this backend yet.
                </Empty>
              )}
            </>
          ) : view === "assistant" ? (
            <Heading
              eyebrow="MISSION SUPPORT"
              title="Health assistant"
              subtitle="Ask a question and review the sources behind each answer."
            />
          ) : (
            <Settings mission={mission} mode={mode} />
          )}
          <Agent
            key={`${mode}:${personal ? (mission.data.session?.crewMember.id ?? "pending") : "control"}`}
            floating={personal}
            fullPage={!personal && view === "assistant"}
            mode={mode}
            askAssistant={askAssistant}
            voice={voice}
            speak={speak}
            identity={
              personal ? mission.data.session?.crewMember.name : undefined
            }
          />
          <footer className="mission-footer">
            <span>ODYSSEY HEALTH MONITOR · UX CONCEPT</span>
            <span>
              {mode === "demo" ? "DEMONSTRATION DATA" : "BACKEND DATA ADAPTER"}
            </span>
          </footer>
        </main>
        {mission.notice && (
          <div className="mission-toast" role="status">
            {mission.notice}
          </div>
        )}
      </div>
    </div>
  );
}
