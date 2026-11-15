# -*- coding: utf-8 -*-
"""Generator of the architecture plan and the interactive artifact.

Single source: data.py (data), template.md (text) and page.html (artifact).
Do not edit docs/architecture-plan.md by hand: change the source and regenerate.

Usage:  python tools/docgen/build.py --artifact-url URL
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from data import *  # noqa: E402,F403

SP = pathlib.Path(__file__).parent
ROOT = SP.parents[1]
MOD = {m["key"]: m for m in MODULES}
NAME = {k: v["name"] for k, v in MOD.items()}
NAME.update(EXTERNALS)
CANAL = {"REST": "REST", "GQL": "GraphQL", "WS": "WebSocket", "EVT": "Event (outbox)"}


def esc(s):
    return str(s).replace("|", "\\|")


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        out.append("| " + " | ".join(esc(c) for c in r) + " |")
    return "\n".join(out)


def names(keys):
    return ", ".join(NAME[k] for k in keys)


# ---------- principles and ADRs ----------
def principles_md():
    return "\n".join(f"{i}. **{t}.** {d}" for i, (t, d) in enumerate(PRINCIPLES, 1))


def adrs_md():
    return table(["ID", "Decision", "Reason and consequence"], [(a, f"**{t}**", d) for a, t, d in ADRS])


# ---------- module map ----------
def module_map_md():
    groups = {}
    for r in ROWS:
        if r[1] != "EVT":
            continue
        for dst in r[4]:
            groups.setdefault((r[3], dst), []).append(r[2].split(".", 1)[1])
    lines = ["```mermaid", "flowchart LR"]
    for m in MODULES:
        if m["key"] == "platform":
            continue
        lines.append(f'  {m["short"]}["{m["name"]}"]')
    lines.append("  classDef mod fill:#e8f1f8,stroke:#2b6a8f,color:#0b2a3a")
    lines.append("  class " + ",".join(m["short"] for m in MODULES if m["key"] != "platform") + " mod")
    for (src, dst), evs in groups.items():
        lines.append(f'  {MOD[src]["short"]} -->|"{", ".join(evs)}"| {MOD[dst]["short"]}')
    for src, dst, port, what in SYNC_READS:
        lines.append(f'  {MOD[src]["short"]} -.->|"reads: {port}"| {MOD[dst]["short"]}')
    lines.append("```")
    return "\n".join(lines)


def modules_md():
    rows = []
    for m in MODULES:
        rows.append((
            f'**{m["name"]}** (`{m["key"]}`)', m["role"],
            ", ".join(m["aggregates"]) or "—",
            "; ".join(m["ports_in"]), "; ".join(m["ports_out"]),
        ))
    return table(["Module", "Responsibility", "Aggregates", "Inbound ports", "Outbound ports"], rows)


def sync_md():
    return table(["Reader", "From whom", "Facade", "What for"], [(NAME[a], NAME[b], f"`{p}`", w) for a, b, p, w in SYNC_READS])


# ---------- ER ----------
TBL_MOD = {t: m for m, tabs in ER.items() for t in tabs}


def er_attr(tbl, mod, col):
    name, typ, flags, ref = col
    keys, comment = [], []
    if "PK" in flags:
        keys.append("PK")
    if "UK" in flags:
        keys.append("UK")
    if ref and TBL_MOD[ref] == mod:
        keys.append("FK")
    if ref and TBL_MOD[ref] != mod:
        comment.append(f"soft ref to {TBL_MOD[ref]}.{ref}")
    if "N" in flags:
        comment.append("null")
    k = (" " + ", ".join(keys)) if keys else ""
    c = (' "' + " · ".join(comment) + '"') if comment else ""
    return f"    {typ} {name}{k}{c}"


def er_rels(tables):
    out = []
    for t, cols in tables.items():
        mod = TBL_MOD[t]
        for name, typ, flags, ref in cols:
            if ref:
                left = "|o" if "N" in flags else "||"
                line = "--" if TBL_MOD[ref] == mod else ".."
                out.append(f'  {ref.upper()} {left}{line}o{{ {t.upper()} : "{name}"')
    return out


def er_module_md(mod):
    tabs = ER[mod]
    lines = ["```mermaid", "erDiagram"]
    for t, cols in tabs.items():
        lines.append(f"  {t.upper()} {{")
        for c in cols:
            lines.append(er_attr(t, mod, c))
        lines.append("  }")
    lines += er_rels(tabs)
    lines.append("```")
    return "\n".join(lines)


ER_ORDER = ["crew", "facility", "telemetry", "monitoring", "knowledge", "assistant", "engagement", "groundlink", "platform"]


def er_all_md():
    parts = []
    for i, mod in enumerate(ER_ORDER):
        parts.append(f"### 7.{i+2} Schema `{mod}` · {NAME[mod]}\n\n" + er_module_md(mod))
    return "\n\n".join(parts)


def er_overview_md():
    allt = {t: c for m in ER.values() for t, c in m.items()}
    lines = ["```mermaid", "erDiagram"] + er_rels(allt) + ["```"]
    return "\n".join(lines)


# ---------- sequences ----------
ARROW = {"call": "->>", "async": "-)", "ret": "-->>", "self": "->>"}


def seq_md(s):
    lines = ["```mermaid", "sequenceDiagram", "  autonumber"]
    for p in s["cast"]:
        lines.append(f"  participant {p} as {SEQ_PARTICIPANTS[p]}")
    for a, b, label, kind, _ in s["steps"]:
        lines.append(f"  {a}{ARROW[kind]}{b}: {label}")
    lines.append("```")
    legend = "\n".join(f"{i}. {d}" for i, (_, _, l, _, d) in enumerate(s["steps"], 1))
    return "\n".join(lines) + "\n\nWhat happens at each step:\n\n" + legend


def seqs_md():
    parts = []
    for i, s in enumerate(SEQS):
        parts.append(f"### 8.{i+1} {s['title']}\n\n{s['subtitle']}\n\n" + seq_md(s))
    return "\n\n".join(parts)


# ---------- channel tables ----------
def rows_of(canal):
    return [r for r in ROWS if r[1] == canal]


def rest_md():
    return table(["ID", "Method and route", "Origin → destination", "What it does", "Payload", "Response"],
                 [(r[0], f"`{r[2]}`", f"{NAME[r[3]]} → {names(r[4])}", r[5], r[6], r[7]) for r in rows_of("REST")])


def gql_md():
    return table(["ID", "Operation", "Owner module", "What it does", "Returns", "Notes"],
                 [(r[0], f"`{r[2]}`", NAME[r[8]], r[5], r[6], r[7]) for r in rows_of("GQL")])


def ws_md():
    return table(["ID", "Message", "Direction", "What it does", "Payload", "Delivery"],
                 [(r[0], f"`{r[2]}`", f"{NAME[r[3]] if r[3] != 'realtime' else 'Server'} → {'Client' if r[4][0] == 'ui' else 'Server'}", r[5], r[6], r[7]) for r in rows_of("WS")])


def evt_md():
    return table(["ID", "Event", "Emitter", "Receivers", "When", "Payload", "Guarantees"],
                 [(r[0], f"`{r[2]}`", NAME[r[3]], names(r[4]), r[5], r[6], r[7]) for r in rows_of("EVT")])


def matrix_md():
    mods = [m for m in MODULES if m["key"] not in ("platform",)]
    heads = ["Emitter \\ Receiver"] + [m["short"] for m in mods]
    rows = []
    for src in mods:
        row = [f'{src["short"]} · {src["name"]}']
        for dst in mods:
            ev = sorted({r[2].split(".", 1)[1] for r in ROWS if r[1] == "EVT" and r[3] == src["key"] and dst["key"] in r[4]})
            row.append(", ".join(ev) if ev else "")
        rows.append(row)
    return table(heads, rows)


def profiles_md():
    return table(["Port", "dev1", "dev2", "jury"], PROFILES)


def journey_md():
    return table(["Stage", "What it needs", "What it sees", "What happens in the system", "How we know it works"],
                 [(j["title"], j["goal"], j["sees"], j["system"], j["metric"]) for j in JOURNEY])


def roadmap_md():
    rows = [(f, n, p, f"{h} h", f"{ALLOC[f][0]} h", f"{ALLOC[f][1]} h", "; ".join(t)) for f, n, p, h, t in ROADMAP]
    p0 = sum(h for _, _, p, h, _ in ROADMAP if p == "P0")
    tot = sum(h for _, _, _, h, _ in ROADMAP)
    a0 = sum(ALLOC[f][0] for f, _, p, _, _ in ROADMAP if p == "P0"); b0 = sum(ALLOC[f][1] for f, _, p, _, _ in ROADMAP if p == "P0")
    return table(["Phase", "Name", "Priority", "Total", "Dev A", "Dev B", "Deliverables"], rows) + f"\n\nThe P0 cut adds up to {p0} h for one person. The full plan is {tot} h. Split between two developers, P0 is {a0} h for A and {b0} h for B, and the full plan is {sum(a for a, _ in ALLOC.values())} h for A and {sum(b for _, b in ALLOC.values())} h for B (see section 16)."


# ---------- split between two developers ----------
PH = {r[0]: r for r in ROADMAP}


def schedule():
    blocks = {"A": [], "B": []}
    end = {"A": 0.0, "B": 0.0}
    idx = {"A": 0, "B": 0}
    sched = {}  # phase -> {lane: (start, end)}
    LH = {"A": 0, "B": 1}

    def ready(f):
        for d in DEPENDS.get(f, []):
            for ln in "AB":
                if ALLOC[d][LH[ln]] > 0 and ln not in sched.get(d, {}):
                    return None
        return max([max(v[1] for v in sched[d].values()) for d in DEPENDS.get(f, []) if d in sched] + [0])

    def put(ln, f, start):
        h = ALLOC[f][LH[ln]]
        sched.setdefault(f, {})[ln] = (start, start + h)
        blocks[ln].append(dict(lane=ln, f=f, name=PH[f][1], prio=PH[f][2], start=start, h=h, end=start + h, rag=f in RAG_PHASES, tasks=PH[f][4], mock=MOCKS.get(f, "")))
        end[ln] = start + h
        idx[ln] += 1

    progress = True
    while progress:
        progress = False
        for ln in "AB":
            while idx[ln] < len(QUEUE[ln]):
                f = QUEUE[ln][idx[ln]]
                dep = ready(f)
                if dep is None:
                    break
                if f == "F9":
                    other = "B" if ln == "A" else "A"
                    if idx[other] < len(QUEUE[other]) and QUEUE[other][idx[other]] == "F9":
                        st = max(end["A"], end["B"], dep)
                        put("A", f, st); put("B", f, st); progress = True
                    break
                st = max(end[ln], dep)
                if ln == "B" and f in ("F10", "F11"):
                    if "A" not in sched.get(f, {}):
                        break
                    st = max(st, sched[f]["A"][1])
                put(ln, f, st); progress = True
    assert idx["A"] == len(QUEUE["A"]) and idx["B"] == len(QUEUE["B"]), (idx, end)
    ph_end = {f: max(v[1] for v in lanes.values()) for f, lanes in sched.items()}
    ms = [dict(id=i, name=n, phase=f, at=ph_end[f], what=w) for i, n, f, w in MILESTONES]
    return blocks, ms


def fmt(h):
    return f"{h:g}"


def owner_md():
    rows = []
    for m in MODULES:
        k = m["key"]
        rows.append((f"{m['name']} (`{k}`)", f"Dev {OWNER[k]}", ", ".join(m["aggregates"]) or "—"))
    rows.append(("Interface (React SPA)", "Dev B", "Cabin panel, ship panel, tasks, assistant, Ground panel"))
    return table(["Module", "Owner", "Aggregates"], rows)


def alloc_md():
    rows = []
    for f, n, p, h, t in ROADMAP:
        a, b2 = ALLOC[f]
        rows.append((f, n, p, f"{fmt(a)} h" if a else "—", f"{fmt(b2)} h" if b2 else "—", "RAG" if f in RAG_PHASES else ""))
    sa = sum(a for a, _ in ALLOC.values()); sb = sum(b for _, b in ALLOC.values())
    return table(["Phase", "Name", "Priority", "Dev A", "Dev B", "RAG"], rows) + f"\n\n**Total:** Dev A {fmt(sa)} h, Dev B {fmt(sb)} h."


def lane_md(ln):
    blocks, _ = schedule()
    rows = [(f"{fmt(b['start'])} to {fmt(b['end'])}", b["f"], b["name"], b["prio"], f"{fmt(b['h'])} h", "RAG" if b["rag"] else "", b["mock"] or "—") for b in blocks[ln]]
    return table(["Hours", "Phase", "Name", "Priority", "Effort", "RAG", "Relies on (until A finishes)"], rows)


def gantt_md():
    from datetime import datetime, timedelta
    blocks, ms = schedule()
    base = datetime(2026, 1, 1, 0, 0)
    ts = lambda h: (base + timedelta(minutes=round(h * 60))).strftime("%Y-%m-%d %H:%M")
    L = ["```mermaid", "gantt", "  title Timeline per developer (D01 is working day 1. Hours are per person, not wall-clock)", "  dateFormat YYYY-MM-DD HH:mm", "  axisFormat D%d %Hh", "  todayMarker off"]
    for ln in "AB":
        L.append(f"  section {DEVS[ln]}")
        for b2 in blocks[ln]:
            tag = "crit, " if b2["rag"] else ""
            L.append(f"  {b2['f']} {" ".join(b2['name'].replace(':', ' ').split())} :{tag}{ln.lower()}{b2['f'].lower()}, {ts(b2['start'])}, {max(1, round(b2['h'] * 60))}m")
    L.append("  section Integration milestones")
    for m in ms:
        L.append(f"  {m['id']} {m['name']} :milestone, {m['id'].lower()}, {ts(m['at'])}, 0d")
    L.append("```")
    return "\n".join(L)


def milestones_md():
    _, ms = schedule()
    return table(["Milestone", "When (h)", "What it unblocks", "Detail"], [(m["id"], fmt(m["at"]), m["name"], m["what"]) for m in sorted(ms, key=lambda x: x["at"])])


def cross_md():
    ev = []
    for r in ROWS:
        if r[1] != "EVT":
            continue
        em = OWNER[r[3]]
        rec = [x for x in r[4] if OWNER[x] != em]
        if rec:
            ev.append((f"`{r[2]}`", f"Dev {em} · {NAME[r[3]]}", ", ".join(f"{NAME[x]} (Dev {OWNER[x]})" for x in rec), r[6]))
    rd = [(f"{NAME[a]} (Dev {OWNER[a]})", f"{NAME[b2]} (Dev {OWNER[b2]})", f"`{p}`", w) for a, b2, p, w in SYNC_READS if OWNER[a] != OWNER[b2]]
    api = {"REST": 0, "GQL": 0, "WS": 0}
    for r in ROWS:
        if r[1] in api and OWNER.get(r[8]) == "A" and ("ui" in [r[3]] + r[4]):
            api[r[1]] += 1
    return ("**Events that cross from one developer to the other**\n\n" + table(["Event", "Emitter", "Receivers on the other developer's side", "Payload"], ev)
            + "\n\n**Synchronous reads between developers**\n\n" + table(["Reader", "From whom", "Facade", "What for"], rd)
            + f"\n\n**B's interface toward A's core:** {api['GQL']} GraphQL operations, {api['WS']} WebSocket messages and {api['REST']} REST routes. They are frozen in I0 as a schema and consumed with generated types.")


def split_rules_md():
    return "\n".join(f"{i}. **{t}.** {d}" for i, (t, d) in enumerate(SPLIT_RULES, 1))


def split_risks_md():
    return table(["Split risk", "Probability", "Mitigation"], SPLIT_RISKS)


def rag_scope_md():
    return "\n".join(f"- {x}" for x in RAG_SCOPE)


def rag_hours_md():
    h = sum(ALLOC[f][1] for f in RAG_PHASES)
    return f"{fmt(h)} h"


def risks_md():
    return table(["Risk", "Probability", "Mitigation"], RISKS)


def open_md():
    return "\n".join(f"{i}. **{t}.** {d}" for i, (t, d) in enumerate(OPEN, 1))


ZN = {"eng": "Engineering and propulsion", "eclss": "Life support", "lab": "Laboratory", "med": "Infirmary", "bridge": "Control bridge", "air": "Airlock", "store": "Storage", "gym": "Gym", "galley": "Galley and dining", "crew": "Crew quarters", "*": "Any"}
SEVN = {1: "Attention", 2: "Alert", 3: "Critical"}


def itypes_md():
    out = []
    for ck, cn in ICATS:
        rows = [(f"`{k}` {n}", det, f"`{r}`" if r else "—", SEVN[sv], ev, ", ".join(ZN[z] for z in zs), "; ".join(acts))
                for k, c, n, det, r, sv, ev, zs, acts in ITYPES if c == ck]
        out.append(f"**{cn}** ({len(rows)})\n\n" + table(["Type", "Detection", "Rule", "Default severity", "Evidence", "Typical zones", "Suggested actions"], rows))
    n_auto = sum(1 for t in ITYPES if t[3] == "AUTO")
    return "\n\n".join(out) + f"\n\nTotal: {len(ITYPES)} types in {len(ICATS)} categories. {n_auto} are detected by rule (AUTO) and {len(ITYPES) - n_auto} are manual reports (MANUAL)."


def build_md(template, out, artifact_url):
    t = pathlib.Path(template).read_text(encoding="utf-8")
    rep = {
        "PRINCIPLES": principles_md(), "ADRS": adrs_md(), "MODULE_MAP": module_map_md(), "MODULES": modules_md(),
        "SYNC": sync_md(), "ER_OVERVIEW": er_overview_md(), "ER_ALL": er_all_md(), "SEQS": seqs_md(),
        "REST": rest_md(), "GQL": gql_md(), "WS": ws_md(), "EVT": evt_md(), "MATRIX": matrix_md(),
        "PROFILES": profiles_md(), "ITYPES": itypes_md(), "OWNERS": owner_md(), "ALLOC": alloc_md(), "LANE_A": lane_md("A"), "LANE_B": lane_md("B"), "GANTT": gantt_md(), "MILESTONES": milestones_md(), "CROSS": cross_md(), "SPLIT_RULES": split_rules_md(), "SPLIT_RISKS": split_risks_md(), "RAG_SCOPE": rag_scope_md(), "RAG_HOURS": rag_hours_md(), "JOURNEY": journey_md(), "ROADMAP": roadmap_md(), "RISKS": risks_md(), "OPEN": open_md(),
        "ARTIFACT_URL": artifact_url,
    }
    for k, v in rep.items():
        t = t.replace("{{" + k + "}}", v)
    left = [w.split("}}")[0] for w in t.split("{{")[1:]]
    if left:
        sys.exit(f"unresolved placeholders in the template: {', '.join(left[:5])}")
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(t, encoding="utf-8")
    print("md", len(t), "chars")


def build_html(page, out):
    er = {}
    for mod, tabs in ER.items():
        er[mod] = {t: [dict(n=c[0], t=c[1], f=c[2], r=c[3]) for c in cols] for t, cols in tabs.items()}
    payload = dict(
        modules=MODULES, externals=EXTERNALS,
        rows=[dict(id=r[0], ch=r[1], route=r[2], from_=r[3], to=r[4], what=r[5], payload=r[6], delivery=r[7], mod=r[8]) for r in ROWS],
        sync=[dict(a=a, b=b, port=p, what=w) for a, b, p, w in SYNC_READS],
        er=er, tblmod=TBL_MOD,
        participants=SEQ_PARTICIPANTS,
        seqs=[dict(key=s["key"], title=s["title"], subtitle=s["subtitle"], cast=s["cast"],
                   steps=[dict(a=a, b=b, label=l, kind=k, detail=d) for a, b, l, k, d in s["steps"]]) for s in SEQS],
        profiles=PROFILES, journey=JOURNEY,
        roadmap=[dict(id=f, name=n, prio=p, h=h, tasks=t, a=ALLOC[f][0], b=ALLOC[f][1], rag=f in RAG_PHASES) for f, n, p, h, t in ROADMAP],
        risks=[dict(r=a, p=b, m=c) for a, b, c in RISKS],
        principles=[dict(t=a, d=b) for a, b in PRINCIPLES],
        adrs=[dict(id=a, t=b, d=c) for a, b, c in ADRS],
        open=[dict(t=a, d=b) for a, b in OPEN],
        owner=OWNER, devs=DEVS, depends=DEPENDS, ragScope=RAG_SCOPE,
        schedule=dict(blocks=schedule()[0], milestones=schedule()[1]),
        splitRules=[dict(t=a, d=c) for a, c in SPLIT_RULES], splitRisks=[dict(r=a, p=c, m=e) for a, c, e in SPLIT_RISKS],
        icats=[dict(k=k, n=n) for k, n in ICATS],
        itypes=[dict(k=k, c=c, n=n, det=det, rule=r, sev=sv, ev=ev, zones=zs, acts=acts) for k, c, n, det, r, sv, ev, zs, acts in ITYPES],
    )
    t = pathlib.Path(page).read_text(encoding="utf-8")
    t = t.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(t, encoding="utf-8")
    print("html", len(t), "chars")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--artifact-url", default="(added on publish)")
    ap.add_argument("--template", default=str(SP / "template.md"))
    ap.add_argument("--page", default=str(SP / "page.html"))
    ap.add_argument("--out-md", default=str(ROOT / "docs" / "architecture-plan.md"))
    ap.add_argument("--out-html", default=str(SP / "out" / "plan.html"))
    a = ap.parse_args()
    build_md(a.template, a.out_md, a.artifact_url)
    build_html(a.page, a.out_html)


if __name__ == "__main__":
    main()
