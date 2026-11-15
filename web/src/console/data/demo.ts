import type { Command, Gateway, Ground, Task } from "../model";
import { seed } from "./fixtures";
export function demoGateway(): Gateway {
  const data = seed();
  const personalTicketIds = new Set(data.session!.incidents.map((i) => i.id));
  const nominalValues: Record<string, number> = {
    co2_mmhg: 1.2,
    o2_pct: 20.8,
    temperature_c: 22.4,
    pressure_kpa: 101.3,
    humidity_pct: 48,
  };
  const zoneValues = new Map<string, Record<string, number>>(
    data.ship!.zones.map((z) => [
      z.id,
      { ...nominalValues, ...(z.code === "lab" ? { co2_mmhg: 3.4 } : {}) },
    ]),
  );
  const listeners = new Set<() => void>();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const emit = () => {
    data.session = {
      ...data.session!,
      tasks: data.tasks,
      incidents: data.incidents.filter((i) => personalTicketIds.has(i.id)),
    };
    data.streak = data.tasks.filter(
      (t) =>
        t.kind === "SALUD" &&
        t.status === "COMPLETADA" &&
        t.origin !== "TIERRA" &&
        !t.sourceAlertId &&
        !t.incidentId,
    ).length;
    listeners.forEach((fn) => fn());
  };
  const transition = () => {
    clearTimeout(timer);
    const g = data.ground!;
    if (
      !g.link.online ||
      !g.published ||
      ["CONFIRMADO", "RECHAZADO"].includes(g.published.stage)
    )
      return;
    timer = setTimeout(() => {
      if (!g.link.online) return;
      const next: Record<string, NonNullable<Ground["published"]>["stage"]> = {
        EN_COLA: "EN_EL_ENLACE",
        EN_EL_ENLACE: "RECIBIDO",
        RECIBIDO: "APLICADO",
        APLICADO: "CONFIRMADO",
      };
      g.published!.stage = next[g.published!.stage] ?? "CONFIRMADO";
      if (g.published!.stage === "APLICADO" && g.draft) {
        g.appliedVersion = g.draft.version;
        const cancelledIds = new Set(
          g.draft.templates.filter((t) => t.cancelled).map((t) => t.id),
        );
        data.tasks = data.tasks.filter(
          (t) =>
            !t.templateId ||
            !cancelledIds.has(t.templateId) ||
            t.status === "COMPLETADA" ||
            t.origin !== "TIERRA",
        );
        g.templates = g.draft.templates
          .filter((t) => !t.cancelled)
          .map((t) => ({
            ...t,
            status: t.status === "PENDIENTE" ? "APLICADA" : t.status,
          }));
        data.groundPlan = {
          version: g.appliedVersion,
          appliedAt: new Date().toISOString(),
          rejected: [],
        };
        for (const t of g.templates) {
          if (!data.tasks.some((task) => task.templateId === t.id))
            data.tasks.push({
              id: crypto.randomUUID(),
              kind: t.kind,
              origin: "TIERRA",
              title: t.title,
              zoneId: null,
              status: "PENDIENTE",
              dueAt: new Date().toISOString(),
              blockedReason: null,
              effective: null,
              sourceAlertId: null,
              incidentId: null,
              templateId: t.id,
            });
        }
        g.draft = null;
      }
      if (g.published!.stage === "CONFIRMADO")
        g.published!.ackedAt = new Date().toISOString();
      emit();
      transition();
    }, g.link.delaySeconds * 1000);
  };
  const task = (id: string): Task => {
    const t = data.tasks.find((x) => x.id === id);
    if (!t) throw Error("Task not found.");
    return t;
  };
  const own = (id: string) => {
    const t = task(id);
    if (t.origin !== "TRIPULACION")
      throw Error("Only crew-created tasks can be edited or deleted.");
    return t;
  };
  const incident = (id: string) => {
    const i = data.incidents.find((x) => x.id === id);
    if (!i) throw Error("Incident not found.");
    return i;
  };
  const draft = () => {
    const g = data.ground!;
    if (g.published && !["CONFIRMADO", "RECHAZADO"].includes(g.published.stage))
      throw Error("A plan is already in flight.");
    g.draft ??= {
      version: g.appliedVersion + 1,
      templates: structuredClone(g.templates),
    };
    return g.draft;
  };
  const execute = async (c: Command) => {
    switch (c.type) {
      case "acknowledgeAlert": {
        const a = data.alerts.find((a) => a.id === c.id);
        if (!a || a.status === "RESOLVED")
          throw Error("Alert not found or already resolved.");
        a.status = "ACKNOWLEDGED";
        break;
      }
      case "completeTask": {
        const t = task(c.id);
        if (t.incidentId)
          throw Error(
            "Resolve the linked incident to complete this system task.",
          );
        t.status = "COMPLETADA";
        t.effective = c.effective;
        break;
      }
      case "blockTask":
        if (!c.reason.trim()) throw Error("A reason is required.");
        Object.assign(task(c.id), {
          status: "BLOQUEADA",
          blockedReason: c.reason,
        });
        break;
      case "snoozeTask":
        if (c.minutes < 1 || c.minutes > 1440)
          throw Error("Choose between 1 and 1440 minutes.");
        task(c.id).dueAt = new Date(
          Date.now() + c.minutes * 60000,
        ).toISOString();
        break;
      case "createTask":
        if (!c.title.trim()) throw Error("A title is required.");
        data.tasks.push({
          ...c,
          id: crypto.randomUUID(),
          status: "PENDIENTE",
          origin: "TRIPULACION",
          effective: null,
          blockedReason: null,
          sourceAlertId: null,
          incidentId: null,
          templateId: null,
        });
        break;
      case "updateTask":
        if (!c.title.trim()) throw Error("A title is required.");
        Object.assign(own(c.id), {
          title: c.title,
          zoneId: c.zoneId,
          dueAt: c.dueAt,
        });
        break;
      case "deleteTask":
        own(c.id);
        data.tasks = data.tasks.filter((t) => t.id !== c.id);
        break;
      case "reportIncident": {
        const type = data.incidentTypes.find((t) => t.key === c.typeKey);
        if (!type) throw Error("Unknown incident type.");
        if (!data.ship?.zones.some((z) => z.id === c.zoneId))
          throw Error("Unknown zone.");
        if (c.severity === "NORMAL")
          throw Error("Incident severity cannot be Nominal.");
        const reportId = crypto.randomUUID();
        personalTicketIds.add(reportId);
        data.incidents.unshift({
          id: reportId,
          code: `INC-${String(11 + data.incidents.length).padStart(4, "0")}`,
          title: type.name,
          description: c.description,
          severity: c.severity ?? type.defaultSeverity,
          status: "ABIERTA",
          source: "MANUAL",
          zoneId: c.zoneId,
          openedAt: new Date().toISOString(),
          valuesNormal: false,
          sourceAlertId: null,
          updates: [],
        });
        break;
      }
      case "acknowledgeIncident": {
        const i = incident(c.id);
        if (i.status === "RESUELTA")
          throw Error("This incident is already resolved.");
        i.status = "RECONOCIDA";
        i.updates.push({
          kind: "ACKNOWLEDGED",
          note: "Acknowledged by demo crew.",
          at: new Date().toISOString(),
        });
        break;
      }
      case "resolveIncident": {
        const i = incident(c.id);
        if (
          i.source === "ALERTA" &&
          data.alerts.some(
            (a) => a.zoneId === i.zoneId && a.status !== "RESOLVED",
          )
        )
          throw Error("Active alerts prevent resolution.");
        i.status = "RESUELTA";
        i.updates.push({
          kind: "RESOLVED",
          note: c.note,
          at: new Date().toISOString(),
        });
        break;
      }
      case "saveGroundTemplate": {
        if (!c.title.trim()) throw Error("A title is required.");
        const d = draft();
        const t = d.templates.find((t) => t.id === c.templateId);
        if (t)
          Object.assign(t, {
            title: c.title,
            kind: c.kind,
            zoneCode: c.zoneCode,
            recurrence: c.recurrence,
          });
        else
          d.templates.push({
            id: crypto.randomUUID(),
            title: c.title,
            kind: c.kind,
            zoneCode: c.zoneCode,
            recurrence: c.recurrence,
            status: "PENDIENTE",
            blockedReason: null,
            cancelled: false,
          });
        break;
      }
      case "cancelGroundTemplate": {
        const d = draft();
        const t = d.templates.find((t) => t.id === c.templateId);
        if (!t) throw Error("Template not found.");
        if (data.ground!.templates.some((t) => t.id === c.templateId))
          t.cancelled = true;
        else d.templates = d.templates.filter((t) => t.id !== c.templateId);
        break;
      }
      case "publishGroundPlan": {
        const g = data.ground!;
        if (!g.draft) throw Error("There are no changes to publish.");
        if (
          g.published &&
          !["CONFIRMADO", "RECHAZADO"].includes(g.published.stage)
        )
          throw Error("A plan is already in flight.");
        g.published = {
          version: g.draft.version,
          stage: g.link.online ? "EN_EL_ENLACE" : "EN_COLA",
          reason: null,
          publishedAt: new Date().toISOString(),
          ackedAt: null,
        };
        transition();
        break;
      }
      case "setGroundLink":
        data.ground!.link = {
          online: c.online,
          delaySeconds: c.delaySeconds,
          changedAt: new Date().toISOString(),
        };
        transition();
        break;
      case "setConsent":
        data.session!.sharedTasks = c.shared;
        break;
      case "recordBaseline":
        if (!Number.isFinite(c.value) || c.value <= 0)
          throw Error("Enter a valid positive baseline.");
        data.session!.baselines = [
          ...(data.session!.baselines ?? []).filter(
            (b) => b.metric !== c.metric,
          ),
          {
            metric: c.metric,
            value: c.value,
            recordedAt: new Date().toISOString(),
          },
        ];
        break;
      case "syncGroundLinkNow":
        transition();
        break;
      case "scenario": {
        const zone = data.ship!.zones.find((z) => z.code === c.zone);
        if (!zone) throw Error("Unknown zone code.");
        const supported: Record<
          string,
          { metric: string; value: number; title: string }
        > = {
          co2_slow: {
            metric: "co2_mmhg",
            value: 3.4,
            title: "Elevated CO₂ trend",
          },
          pressure_leak: {
            metric: "pressure_kpa",
            value: 30,
            title: "Simulated pressure loss",
          },
          humidity_high: {
            metric: "humidity_pct",
            value: 80,
            title: "Simulated high humidity",
          },
          o2_failure: {
            metric: "o2_pct",
            value: 12,
            title: "Simulated oxygen failure",
          },
          heat: {
            metric: "temperature_c",
            value: 30,
            title: "Simulated high temperature",
          },
        };
        const scenario = supported[c.key];
        if (!scenario) throw Error("Unknown scenario.");
        if (c.action === "stop") {
          data.alerts
            .filter(
              (a) => a.zoneId === zone.id && a.ruleKey === `demo-${c.key}`,
            )
            .forEach((a) => (a.status = "RESOLVED"));
          data.incidents
            .filter((i) => i.zoneId === zone.id && i.source === "ALERTA")
            .forEach(
              (i) =>
                (i.valuesNormal = !data.alerts.some(
                  (a) => a.zoneId === zone.id && a.status !== "RESOLVED",
                )),
            );
          const nominal = nominalValues;
          zoneValues.get(zone.id)![scenario.metric] = nominal[scenario.metric];
          const reading = data.dashboard!.vitals.find(
            (v) => v.key === scenario.metric,
          );
          if (reading) {
            reading.value = nominal[scenario.metric];
            reading.severity = "NORMAL";
          }
        } else {
          const existing = data.alerts.find(
            (a) =>
              a.zoneId === zone.id &&
              a.ruleKey === `demo-${c.key}` &&
              a.status !== "RESOLVED",
          );
          if (!existing) {
            const id = crypto.randomUUID();
            const at = new Date().toISOString();
            const fixture = seed().alerts[0];
            data.alerts.push({
              ...fixture,
              id,
              ruleKey: `demo-${c.key}`,
              zoneId: zone.id,
              raisedAt: at,
            });
            data.incidents.unshift({
              id: crypto.randomUUID(),
              code: `INC-${String(11 + data.incidents.length).padStart(4, "0")}`,
              title: scenario.title,
              description:
                "Fictional scenario event. No operational guidance is implied.",
              severity: "ALERTA",
              status: "ABIERTA",
              source: "ALERTA",
              zoneId: zone.id,
              openedAt: at,
              valuesNormal: false,
              sourceAlertId: id,
              updates: [],
            });
          }
          zoneValues.get(zone.id)![scenario.metric] = scenario.value;
          const reading = data.dashboard!.vitals.find(
            (v) => v.key === scenario.metric,
          );
          if (reading) {
            reading.value = scenario.value;
            reading.severity = "ALERTA";
            reading.zoneId = zone.id;
          }
        }
        data.dashboard!.globalSeverity = data.alerts.some(
          (a) => a.status !== "RESOLVED",
        )
          ? "ALERTA"
          : "NORMAL";
        break;
      }
    }
    data.ship?.zones.forEach((z) => {
      const active = data.incidents.filter(
        (i) => i.zoneId === z.id && i.status !== "RESUELTA",
      );
      z.openIncidents = active.length;
      z.status = active.reduce(
        (s, i) =>
          ["NORMAL", "ATENCION", "ALERTA", "CRITICO"].indexOf(i.severity) >
          ["NORMAL", "ATENCION", "ALERTA", "CRITICO"].indexOf(s)
            ? i.severity
            : s,
        "NORMAL" as import("../model").Severity,
      );
    });
    emit();
  };
  return {
    read: async () => structuredClone(data),
    execute,
    series: async (zoneId, from, to) => {
      const values = zoneValues.get(zoneId);
      if (!values) throw Error("Unknown zone.");
      const start = new Date(from).getTime();
      const finish = new Date(to).getTime();
      if (!Number.isFinite(start) || !Number.isFinite(finish) || finish < start)
        throw Error("Invalid history window.");
      return [
        "co2_mmhg",
        "o2_pct",
        "temperature_c",
        "pressure_kpa",
        "humidity_pct",
      ].map((metric, i) => ({
        metric,
        unit: ["mmHg", "%", "°C", "kPa", "%"][i],
        points: Array.from({ length: 60 }, (_, n) => {
          const avg =
            values[metric] +
            Math.sin((n - 59) * 0.3) * [0.12, 0.1, 0.3, 0.05, 1][i];
          return {
            ts: new Date(start + ((finish - start) * n) / 59).toISOString(),
            avg,
            min: avg - 0.02,
            max: avg + 0.02,
          };
        }),
      }));
    },
    subscribe: (listener, status) => {
      listeners.add(listener);
      status("Demo stream");
      return () => listeners.delete(listener);
    },
    dispose: () => {
      clearTimeout(timer);
      listeners.clear();
    },
  };
}
