import { useState } from "react";
import type { Mission } from "../data/useMission";
import { label, time, type Template } from "../model";
import { Empty, Heading, Modal, Panel } from "../ui/Common";
export function GroundPage({ mission }: { mission: Mission }) {
  const [form, setForm] = useState<Template | true | null>(null);
  const [delay, setDelay] = useState<number | null>(null);
  const g = mission.data.ground;
  const inflight =
    g?.published && !["CONFIRMADO", "RECHAZADO"].includes(g.published.stage);
  const templates = g?.draft?.templates ?? g?.templates ?? [];
  return (
    <>
      <Heading
        eyebrow="GROUND OPERATIONS · CONTROL CENTER"
        title="Ground control"
        subtitle="Prepare versioned task plans and follow delivery to the habitat."
        actions={
          <button
            className="button primary"
            disabled={!g || mission.pending || !!inflight}
            onClick={() => setForm(true)}
          >
            ＋ Add template
          </button>
        }
      />
      {!g ? (
        <Empty>Ground-control data is not available.</Empty>
      ) : (
        <div className="ground-layout">
          <div>
            <Panel
              title="Plan templates"
              subtitle={`Applied plan v${g.appliedVersion}${g.draft ? " · Draft v" + g.draft.version : ""}`}
              actions={
                <button
                  className="button primary"
                  disabled={mission.pending || !g.draft || !!inflight}
                  onClick={() =>
                    void mission.run({ type: "publishGroundPlan" })
                  }
                >
                  Publish plan{g.draft ? " v" + g.draft.version : ""}
                </button>
              }
            >
              {templates.length ? (
                templates.map((t) => (
                  <article className="template-item" key={t.id}>
                    <div className="template-mark">
                      {t.kind === "SALUD" ? "✚" : "⌘"}
                    </div>
                    <div className="item-copy">
                      <h3>{t.title}</h3>
                      <p>
                        {label(t.kind)} ·{" "}
                        {t.cancelled
                          ? "Cancellation in draft"
                          : label(t.status)}
                      </p>
                      {t.blockedReason && <p>Blocked: {t.blockedReason}</p>}
                    </div>
                    <button
                      className="button subtle"
                      disabled={mission.pending || !!inflight || t.cancelled}
                      onClick={() => setForm(t)}
                    >
                      Edit
                    </button>
                    <button
                      className="button subtle"
                      disabled={mission.pending || !!inflight || t.cancelled}
                      onClick={() =>
                        void mission.run({
                          type: "cancelGroundTemplate",
                          templateId: t.id,
                        })
                      }
                    >
                      Cancel
                    </button>
                  </article>
                ))
              ) : (
                <Empty>No plan templates.</Empty>
              )}
            </Panel>
            <Panel
              title="Plan delivery"
              subtitle="Publication and acknowledgement are separate states"
            >
              {g.published ? (
                <>
                  <ol
                    className="pipeline"
                    aria-label={`Plan v${g.published.version} delivery`}
                  >
                    {[
                      "EN_COLA",
                      "EN_EL_ENLACE",
                      "RECIBIDO",
                      "APLICADO",
                      "CONFIRMADO",
                    ].map((stage) => (
                      <li
                        key={stage}
                        aria-current={
                          stage === g.published!.stage ? "step" : undefined
                        }
                      >
                        {label(stage)}
                      </li>
                    ))}
                  </ol>
                  <dl>
                    <dt>Published version</dt>
                    <dd>v{g.published.version}</dd>
                    <dt>Stage</dt>
                    <dd>{label(g.published.stage)}</dd>
                    <dt>Published</dt>
                    <dd>{time(g.published.publishedAt)}</dd>
                    <dt>Acknowledged</dt>
                    <dd>
                      {g.published.ackedAt
                        ? time(g.published.ackedAt)
                        : "Awaiting confirmation"}
                    </dd>
                  </dl>
                  {g.published.reason && (
                    <p role="alert">{g.published.reason}</p>
                  )}
                </>
              ) : (
                <Empty>No plan has been published.</Empty>
              )}
            </Panel>
          </div>
          <div>
            <Panel
              title="Mission communication"
              subtitle="Earth link · Independent of the local mission backend"
            >
              <div className="link-state">
                <i className={`dot ${g.link.online ? "online" : ""}`} />
                <b>{g.link.online ? "Link connected" : "Link interrupted"}</b>
                <button
                  className="button"
                  disabled={mission.pending}
                  onClick={() =>
                    void mission.run({
                      type: "setGroundLink",
                      online: !g.link.online,
                      delaySeconds: g.link.delaySeconds,
                    })
                  }
                >
                  {g.link.online ? "Cut link" : "Restore link"}
                </button>
              </div>
              <label className="field">
                Delivery delay (seconds)
                <input
                  type="number"
                  min="0"
                  max="3600"
                  value={delay ?? g.link.delaySeconds}
                  onChange={(e) => setDelay(Number(e.target.value))}
                />
              </label>
              <button
                className="button"
                disabled={
                  mission.pending ||
                  delay === null ||
                  !Number.isInteger(delay) ||
                  delay < 0 ||
                  delay > 3600
                }
                onClick={() =>
                  void mission.run({
                    type: "setGroundLink",
                    online: g.link.online,
                    delaySeconds: delay ?? g.link.delaySeconds,
                  })
                }
              >
                Apply delay
              </button>
              <button
                className="button subtle"
                disabled={mission.pending || !g.link.online}
                onClick={() => void mission.run({ type: "syncGroundLinkNow" })}
              >
                Sync now
              </button>
              <p className="muted">
                {g.link.online
                  ? "Plan delivery can proceed."
                  : "Published plans remain queued until the link is restored."}
              </p>
            </Panel>
            <Panel
              title="Crew task sharing"
              subtitle="Consent-aware visibility"
            >
              <p>
                Ground receives only task information permitted by crew consent.
                Personal health measurements are not included in this plan view.
              </p>
              <p className="muted">
                Visibility and blocked reasons must be filtered by the backend.
              </p>
            </Panel>
          </div>
        </div>
      )}
      {form && (
        <Modal
          title={form === true ? "Add a template" : "Edit template"}
          onClose={() => setForm(null)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              void mission
                .run({
                  type: "saveGroundTemplate",
                  title: String(f.get("title")).trim(),
                  kind: f.get("kind") as "SALUD" | "NAVE",
                  zoneCode: String(f.get("zone")) || null,
                  recurrence: f.get("recurrence") as "DIARIA" | "UNA_VEZ",
                  templateId: form === true ? undefined : form.id,
                })
                .then((ok) => {
                  if (ok) setForm(null);
                });
            }}
          >
            <label className="field">
              Title
              <input
                name="title"
                required
                maxLength={180}
                defaultValue={form === true ? "" : form.title}
              />
            </label>
            <label className="field">
              Category
              <select
                name="kind"
                defaultValue={form === true ? "SALUD" : form.kind}
              >
                <option value="SALUD">Health</option>
                <option value="NAVE">Habitat</option>
              </select>
            </label>
            <label className="field">
              Zone
              <select
                name="zone"
                defaultValue={form === true ? "" : (form.zoneCode ?? "")}
              >
                <option value="">No zone</option>
                {mission.data.ship?.zones.map((z) => (
                  <option key={z.id} value={z.code}>
                    {z.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Recurrence
              <select
                name="recurrence"
                defaultValue={
                  form === true ? "DIARIA" : (form.recurrence ?? "DIARIA")
                }
              >
                <option value="DIARIA">Daily</option>
                <option value="UNA_VEZ">Once</option>
              </select>
            </label>
            <button className="button primary" disabled={mission.pending}>
              Save draft template
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}
