import { useState } from "react";
import type { Task, Zone, Command } from "../model";
import { label, time } from "../model";
import { Empty, Modal, Panel } from "./Common";
interface Props {
  tasks: Task[];
  zones: Zone[];
  run: (command: Command) => Promise<boolean>;
  pending: boolean;
  routine?: boolean;
}
export function TaskPanel({
  tasks,
  zones,
  run,
  pending,
  routine = false,
}: Props) {
  const [filter, setFilter] = useState("pending");
  const [kind, setKind] = useState("all");
  const [selected, setSelected] = useState<Task | null>(null);
  const [form, setForm] = useState<"create" | "edit" | null>(null);
  const [reason, setReason] = useState("");
  const [effective, setEffective] = useState("unknown");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const task = tasks.find((t) => t.id === selected?.id) ?? selected;
  const filtered = tasks.filter(
    (t) =>
      (kind === "all" || t.kind === kind) &&
      (filter === "all" ||
        (filter === "pending"
          ? t.status !== "COMPLETADA"
          : t.status === "COMPLETADA")),
  );
  const open = (t: Task) => {
    setSelected(t);
    setReason("");
    setEffective("unknown");
    setConfirmDelete(false);
  };
  const save = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const f = new FormData(event.currentTarget);
    const title = String(f.get("title")).trim();
    const raw = String(f.get("dueAt") ?? "");
    const dueAt = raw ? new Date(raw + "Z").toISOString() : null;
    const zoneId = String(f.get("zoneId")) || null;
    const command: Command =
      form === "edit" && task
        ? { type: "updateTask", id: task.id, title, zoneId, dueAt }
        : {
            type: "createTask",
            title,
            zoneId,
            dueAt,
            kind: f.get("kind") as "SALUD" | "NAVE",
          };
    if (await run(command)) {
      setForm(null);
      setSelected(null);
    }
  };
  const done = tasks.filter((t) => t.status === "COMPLETADA").length;
  return (
    <Panel
      title={routine ? "My routine" : "Tasks"}
      subtitle={
        routine
          ? "Personal schedule · UTC · shared completion state"
          : `${done} of ${tasks.length} complete · ${tasks.length - done} pending`
      }
      actions={
        <button
          className="button primary"
          onClick={() => {
            setSelected(null);
            setForm("create");
          }}
        >
          ＋ Create task
        </button>
      }
    >
      <div className="filter-toolbar">
        <div className="segments" aria-label="Task status">
          {["pending", "completed", "all"].map((v) => (
            <button
              key={v}
              aria-pressed={filter === v}
              onClick={() => setFilter(v)}
            >
              {v[0].toUpperCase() + v.slice(1)}
            </button>
          ))}
        </div>
        <label className="compact-label">
          Category
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="all">All categories</option>
            <option value="SALUD">Health</option>
            <option value="NAVE">Habitat</option>
            <option value="INCIDENTE">Incidents</option>
          </select>
        </label>
      </div>
      <div className={routine ? "routine-grid" : "task-list"}>
        {filtered.length ? (
          filtered
            .slice()
            .sort((a, b) => (a.dueAt ?? "").localeCompare(b.dueAt ?? ""))
            .map((t) => (
              <article
                className={`task-item ${t.status === "COMPLETADA" ? "complete" : ""}`}
                key={t.id}
              >
                <div className="task-symbol">
                  {t.status === "COMPLETADA"
                    ? "✓"
                    : t.status === "BLOQUEADA"
                      ? "!"
                      : "○"}
                </div>
                <div className="item-copy">
                  <button className="item-title" onClick={() => open(t)}>
                    {t.title}
                  </button>
                  <p>
                    {label(t.kind)} · {label(t.origin)}
                    {t.zoneId
                      ? " · " +
                        (zones.find((z) => z.id === t.zoneId)?.name ?? "Zone")
                      : ""}
                  </p>
                  {t.blockedReason && <p>Blocked: {t.blockedReason}</p>}
                  <span className="tag">{label(t.status)}</span>
                </div>
                <time>{time(t.dueAt)}</time>
              </article>
            ))
        ) : (
          <Empty>
            {filter === "completed"
              ? "No completed activities yet."
              : "No activities in this filter."}
          </Empty>
        )}
      </div>
      {task && !form && (
        <Modal title={task.title} onClose={() => setSelected(null)}>
          <dl>
            <dt>Source</dt>
            <dd>{label(task.origin)}</dd>
            <dt>Category</dt>
            <dd>{label(task.kind)}</dd>
            <dt>Scheduled</dt>
            <dd>{time(task.dueAt)}</dd>
            <dt>Status</dt>
            <dd>{label(task.status)}</dd>
          </dl>
          {task.incidentId && (
            <p className="inline-notice">
              This activity is linked to an incident. Follow the incident
              workflow to resolve it.
            </p>
          )}
          {task.status !== "COMPLETADA" && (
            <>
              <label className="field">
                Did the action help?
                <select
                  value={effective}
                  onChange={(e) => setEffective(e.target.value)}
                >
                  <option value="unknown">Not assessed</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </label>
              <div className="actions">
                <button
                  className="button primary"
                  disabled={pending || !!task.incidentId}
                  onClick={() =>
                    void run({
                      type: "completeTask",
                      id: task.id,
                      effective:
                        effective === "unknown" ? null : effective === "yes",
                    }).then((ok) => {
                      if (ok) setSelected(null);
                    })
                  }
                >
                  Complete task
                </button>
                <button
                  className="button"
                  disabled={pending}
                  onClick={() =>
                    void run({ type: "snoozeTask", id: task.id, minutes: 15 })
                  }
                >
                  Snooze 15 min
                </button>
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void run({
                    type: "blockTask",
                    id: task.id,
                    reason: reason.trim(),
                  }).then((ok) => {
                    if (ok) setSelected(null);
                  });
                }}
              >
                <label className="field">
                  Unable to complete? Give a reason
                  <textarea
                    required
                    maxLength={1500}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                  />
                </label>
                <button className="button" disabled={pending || !reason.trim()}>
                  Report blocker
                </button>
              </form>
            </>
          )}
          {task.origin === "TRIPULACION" && (
            <div className="danger-actions">
              <button
                className="button"
                disabled={pending}
                onClick={() => setForm("edit")}
              >
                Edit own task
              </button>
              {confirmDelete ? (
                <>
                  <span>Delete this task?</span>
                  <button
                    className="button danger"
                    disabled={pending}
                    onClick={() =>
                      void run({ type: "deleteTask", id: task.id }).then(
                        (ok) => {
                          if (ok) setSelected(null);
                        },
                      )
                    }
                  >
                    Confirm delete
                  </button>
                  <button
                    className="button"
                    onClick={() => setConfirmDelete(false)}
                  >
                    Keep task
                  </button>
                </>
              ) : (
                <button
                  className="button danger"
                  onClick={() => setConfirmDelete(true)}
                >
                  Delete own task
                </button>
              )}
            </div>
          )}
        </Modal>
      )}
      {form && (
        <Modal
          title={form === "create" ? "Create a task" : "Edit your task"}
          onClose={() => setForm(null)}
        >
          <form onSubmit={(e) => void save(e)}>
            <label className="field">
              Title
              <input
                name="title"
                required
                maxLength={180}
                defaultValue={form === "edit" ? task?.title : ""}
              />
            </label>
            {form === "create" && (
              <label className="field">
                Category
                <select name="kind">
                  <option value="SALUD">Health</option>
                  <option value="NAVE">Habitat</option>
                </select>
              </label>
            )}
            <label className="field">
              Zone
              <select
                name="zoneId"
                defaultValue={form === "edit" ? (task?.zoneId ?? "") : ""}
              >
                <option value="">Personal workspace</option>
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Scheduled time (UTC)
              <input
                type="datetime-local"
                name="dueAt"
                defaultValue={form === "edit" ? task?.dueAt?.slice(0, 16) : ""}
              />
            </label>
            <p className="muted">
              Created by crew. Works without an Earth link when the local
              backend is available.
            </p>
            <button className="button primary" disabled={pending}>
              Save task
            </button>
          </form>
        </Modal>
      )}
    </Panel>
  );
}
