import { useCallback, useEffect, useMemo, useState } from "react";
import { api, fileUrl, photoUrl, type Check, type Finding, type Spot, type TraceStep } from "../api";
import { navigate, TopBar } from "../App";
import Camera from "../components/Camera";
import Wipe, { verdictText, type Mark } from "../components/Wipe";

const WORK_SIDE = 1024;

function viewSize(spot: Spot) {
  const { w, h } = spot.before;
  const s = Math.min(1, WORK_SIDE / Math.max(w, h));
  return { w: Math.round(w * s), h: Math.round(h * s) };
}

function spotStatus(spot: Spot, sealed: boolean): { text: string; tone: string } {
  if (!sealed) return { text: "Move-in photo", tone: "muted" };
  if (!spot.after) return { text: "Needs move-out photo", tone: "todo" };
  const st = spot.state.status;
  if (st === "retake") return { text: "Retake needed", tone: "todo" };
  if (st === "needs_followup") return { text: "One more photo", tone: "todo" };
  const n = spot.state.findings.filter((f) => f.verdict === "changed").length;
  return { text: n ? `${n} change${n > 1 ? "s" : ""}` : "No changes", tone: n ? "signal" : "done" };
}

function findingTitle(f: Finding) {
  if (f.caption) return f.caption;
  if (f.verdict === "lighting") return f.kind === "glare" ? "Reflection" : "Shadow or light change";
  if (f.verdict === "unchanged") return "Nothing there on a closer look";
  if (f.kind === "object") return "Object added, moved or removed";
  if (f.kind === "glare?") return "Possible reflection";
  return "Surface change";
}

function Trace({ steps }: { steps: TraceStep[] }) {
  return (
    <ol className="trace" aria-label="Agent trace">
      {steps.map((s, i) => (
        <li key={i} style={{ animationDelay: `${Math.min(i, 14) * 70}ms` }}>
          <code className="trace-tool">{s.tool}</code>
          <span className="trace-result">{s.result}</span>
          {s.decision && <span className="trace-decision">→ {s.decision}</span>}
        </li>
      ))}
    </ol>
  );
}

function Findings({ findings, active, setActive }: { findings: Finding[]; active: number | null; setActive: (i: number | null) => void }) {
  if (!findings.length) return <p className="empty">No differences above the noise floor. This spot matches the move-in photo.</p>;
  const order = ["changed", "uncertain", "pending", "lighting", "unchanged"];
  const sorted = findings.map((f, i) => ({ f, i })).sort((a, b) => order.indexOf(a.f.verdict) - order.indexOf(b.f.verdict));
  return (
    <ul className="findings">
      {sorted.map(({ f, i }) => (
        <li
          key={f.id}
          data-active={active === i || undefined}
          onMouseEnter={() => setActive(i)}
          onMouseLeave={() => setActive(null)}
          onFocus={() => setActive(i)}
          onBlur={() => setActive(null)}
          tabIndex={0}
        >
          <div className="finding-head">
            <span className="finding-n mono" data-v={f.verdict}>{i + 1}</span>
            <span className="chip" data-v={f.verdict}>{verdictText(f.verdict)}</span>
            <strong>{findingTitle(f)}</strong>
          </div>
          <ul className="evidence">
            {f.evidence.map((e, k) => (
              <li key={k}>{e}</li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}

function SampleShooter({ ghost, label, busy, onShoot }: { ghost: string; label: string; busy: boolean; onShoot: () => void }) {
  return (
    <div className="sample-shooter">
      <div className="sample-frame" data-busy={busy || undefined}>
        <img src={ghost} alt="Move-in photo of this spot" />
        <div className="scanline" aria-hidden="true" />
      </div>
      <div className="cam-bar">
        <span className="cam-note">Sample check: Twice uses a prepared photo instead of your camera.</span>
        <button className="btn btn-signal" onClick={onShoot} disabled={busy}>
          {busy ? "Analysing…" : label}
        </button>
      </div>
    </div>
  );
}

export default function CheckPage({ id }: { id: string }) {
  const [check, setCheck] = useState<Check | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [label, setLabel] = useState("");
  const [active, setActive] = useState<number | null>(null);
  const [heat, setHeat] = useState(false);

  useEffect(() => {
    api.check(id).then(setCheck).catch((e) => setError(e.message));
  }, [id]);

  const sealed = !!check?.seals.some((s) => s.phase === "before");
  const isSample = !!check?.sample;
  const spot = useMemo(() => {
    if (!check || !sealed) return null;
    return check.spots.find((s) => s.id === selected) ?? check.spots.find((s) => s.state.status !== "done") ?? check.spots[0];
  }, [check, sealed, selected]);

  const replaceSpot = useCallback(
    (s: Spot) => setCheck((c) => c && { ...c, spots: c.spots.map((x) => (x.id === s.id ? s : x)) }),
    [],
  );

  const run = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError("");
    try {
      return await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, []);

  const addBefore = useCallback(
    async (photo: Blob) => {
      const s = await run(() => api.addSpot(id, photo, label));
      if (s) {
        setCheck((c) => c && { ...c, spots: [...c.spots, s] });
        setLabel("");
      }
    },
    [id, label, run],
  );

  const shootAfter = useCallback(
    async (photo?: Blob) => {
      if (!spot) return;
      const pending = spot.after && spot.state.status === "needs_followup";
      const s = await run(() =>
        isSample ? api.sampleShot(id, spot.id) : pending ? api.followup(id, spot.id, photo!) : api.after(id, spot.id, photo!),
      );
      if (s) {
        replaceSpot(s);
        setSelected(s.id);
      }
    },
    [id, spot, isSample, run, replaceSpot],
  );

  const guide = useCallback((frame: Blob) => api.guide(id, spot!.id, frame), [id, spot]);
  const quality = useCallback((frame: Blob) => api.quality(frame), []);

  if (error && !check) {
    return (
      <>
        <TopBar />
        <div className="page-msg">
          <h1>We couldn't open this check.</h1>
          <p>{error}</p>
          <a className="btn" href="#/">Back to the start</a>
        </div>
      </>
    );
  }
  if (!check) {
    return (
      <>
        <TopBar />
        <div className="workspace"><div className="skeleton" style={{ height: 520 }} /></div>
      </>
    );
  }

  const allDone = check.spots.length > 0 && check.spots.every((s) => s.after && s.state.status === "done");
  const phase = !sealed ? 0 : allDone ? 2 : 1;

  return (
    <>
      <TopBar>
        <span className="check-name">{check.name}</span>
      </TopBar>
      <div className="workspace">
        <aside className="rail">
          <ol className="phases" aria-label="Progress">
            {["Move in", "Move out", "Report"].map((p, i) => (
              <li key={p} data-state={i < phase ? "done" : i === phase ? "now" : "next"} aria-current={i === phase ? "step" : undefined}>
                <span className="phase-n">{i + 1}</span>
                {p}
              </li>
            ))}
          </ol>
          <ul className="spots">
            {check.spots.map((s, i) => {
              const st = spotStatus(s, sealed);
              return (
                <li key={s.id}>
                  <button
                    className="spot"
                    data-selected={spot?.id === s.id || undefined}
                    onClick={() => sealed && setSelected(s.id)}
                    disabled={!sealed}
                  >
                    <img src={photoUrl(check.id, s.before)} alt="" loading="lazy" />
                    <span className="spot-text">
                      <span className="spot-label">{s.label}</span>
                      <span className="spot-status" data-tone={st.tone}>{st.text}</span>
                    </span>
                    <span className="spot-n mono">{String(i + 1).padStart(2, "0")}</span>
                  </button>
                </li>
              );
            })}
            {!check.spots.length && <li className="empty">Your spots appear here. Aim for three to six.</li>}
          </ul>
          {!sealed && (
            <button className="btn btn-primary seal-btn" disabled={!check.spots.length || busy} onClick={() => run(() => api.seal(id).then(() => api.check(id)).then(setCheck))}>
              Seal the move-in set
            </button>
          )}
          {allDone && (
            <button className="btn btn-signal seal-btn" disabled={busy} onClick={() => run(() => api.report(id)).then((c) => c && navigate(`/report/${c.id}`))}>
              Create the signed report <span className="arrow" aria-hidden="true">→</span>
            </button>
          )}
          {sealed && <p className="seal-note mono">Move-in set sealed · {check.seals[0].algorithm} · {check.seals[0].digest.slice(0, 12)}…</p>}
        </aside>

        <section className="stage" aria-live="polite">
          {error && <p className="form-error" role="alert">{error}</p>}
          {sealed && !isSample && check.spots.every((s) => !s.after) && <KeepLink id={check.id} name={check.name} />}

          {!sealed && (
            <>
              <header className="stage-head">
                <h1>Move-in photos</h1>
                <p>Shoot each spot you want on record: a wall, a counter, a floor corner, a car panel. Include an edge or a corner so Twice can find the spot again.</p>
              </header>
              <label className="field">
                <span className="label">Name this spot</span>
                <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder={`Spot ${check.spots.length + 1}, for example “Kitchen counter”`} maxLength={60} />
              </label>
              <Camera mode="before" busy={busy} quality={quality} onCapture={addBefore} />
            </>
          )}

          {spot && (!spot.after || spot.state.status === "retake") && (
            <>
              <header className="stage-head">
                <h1>{spot.label}</h1>
                <p>
                  {spot.state.status === "retake"
                    ? "Twice could not match this photo to the move-in photo. Stand where you stood the first time and try again."
                    : "Go back to this spot. The ghost of your move-in photo will guide you to the same angle."}
                </p>
              </header>
              {isSample ? (
                <SampleShooter ghost={photoUrl(check.id, spot.before)} label="Take the move-out photo" busy={busy} onShoot={() => shootAfter()} />
              ) : (
                <Camera mode="guide" ghost={photoUrl(check.id, spot.before)} busy={busy} quality={quality} guide={guide} onCapture={shootAfter} />
              )}
            </>
          )}

          {spot && spot.after && spot.state.status !== "retake" && (
            <Result
              check={check}
              spot={spot}
              busy={busy}
              isSample={isSample}
              active={active}
              setActive={setActive}
              heat={heat}
              setHeat={setHeat}
              quality={quality}
              onFollowup={shootAfter}
              next={check.spots.find((s) => s.id !== spot.id && s.state.status !== "done")}
              onNext={(sid) => setSelected(sid)}
            />
          )}
        </section>
      </div>
    </>
  );
}

function KeepLink({ id, name }: { id: string; name: string }) {
  const [copied, setCopied] = useState(false);
  const url = `${location.origin}${location.pathname}#/check/${id}`;
  const copy = () => navigator.clipboard.writeText(url).then(() => setCopied(true));
  const mail = `mailto:?subject=${encodeURIComponent(`Twice: ${name}`)}&body=${encodeURIComponent(`Open this link at move-out:
${url}`)}`;
  return (
    <div className="keep">
      <div>
        <span className="label">Sealed. Keep this link.</span>
        <p>You need it at move-out. Twice has no accounts, so this link is the only way back to your photos.</p>
        <code className="keep-url">{url}</code>
      </div>
      <div className="keep-actions">
        <button className="btn btn-primary" onClick={copy}>{copied ? "Copied" : "Copy the link"}</button>
        <a className="btn" href={mail}>Email it to me</a>
      </div>
    </div>
  );
}

interface ResultProps {
  check: Check;
  spot: Spot;
  busy: boolean;
  isSample: boolean;
  active: number | null;
  setActive: (i: number | null) => void;
  heat: boolean;
  setHeat: (v: boolean) => void;
  quality: (b: Blob) => Promise<import("../api").Quality>;
  onFollowup: (b?: Blob) => void;
  next?: Spot;
  onNext: (id: string) => void;
}

function Result({ check, spot, busy, isSample, active, setActive, heat, setHeat, quality, onFollowup, next, onNext }: ResultProps) {
  const size = viewSize(spot);
  const pending = spot.state.pending;
  const marks: Mark[] = spot.state.findings.map((f, i) => ({
    n: i + 1,
    box: [f.box[0] / size.w, f.box[1] / size.h, f.box[2] / size.w, f.box[3] / size.h],
    verdict: f.verdict,
    tag:
      f.verdict === "changed"
        ? findingTitle(f)
        : f.verdict === "lighting"
          ? `${f.kind === "glare" ? "Reflection" : "Light change"} · ruled out`
          : verdictText(f.verdict),
  }));
  const pendingIndex = pending ? spot.state.findings.findIndex((f) => f.id === pending.finding) : null;
  const counts = spot.state.findings.reduce<Record<string, number>>((m, f) => ((m[f.verdict] = (m[f.verdict] ?? 0) + 1), m), {});
  const reg = spot.state.registration;

  return (
    <div className="result">
      <header className="stage-head row">
        <div>
          <h1>{spot.label}</h1>
          <p className="summary">
            {counts.changed ? <><b>{counts.changed} changed</b> · </> : <><b>No changes</b> · </>}
            {counts.lighting ?? 0} ruled out · {counts.uncertain ?? 0} can't judge
          </p>
        </div>
        <div className="head-actions">
          <label className="toggle">
            <input type="checkbox" checked={heat} onChange={(e) => setHeat(e.target.checked)} />
            <span>Change map</span>
          </label>
          {next && spot.state.status === "done" && (
            <button className="btn btn-primary" onClick={() => onNext(next.id)}>
              Next: {next.label} <span className="arrow" aria-hidden="true">→</span>
            </button>
          )}
        </div>
      </header>

      {pending && (
        <div className="followup">
          <div className="followup-copy">
            <span className="label">The agent needs one more photo</span>
            <h2>{pending.kind === "parallax" ? "Take one step to the side." : "Move in close."}</h2>
            <p>{pending.prompt}</p>
          </div>
          {isSample ? (
            <button className="btn btn-signal" onClick={() => onFollowup()} disabled={busy}>
              {busy ? "Analysing…" : pending.kind === "parallax" ? "Take the side-step photo" : "Take the close-up"}
            </button>
          ) : (
            <Camera mode="followup" prompt={pending.prompt} busy={busy} quality={quality} onCapture={onFollowup} />
          )}
        </div>
      )}

      <Wipe
        before={fileUrl(check.id, `${spot.id}-view-before.jpg`)}
        after={fileUrl(check.id, `${spot.id}-view-after.jpg`)}
        heat={fileUrl(check.id, `${spot.id}-view-heat.png`)}
        showHeat={heat}
        ratio={size.w / size.h}
        marks={marks}
        active={active ?? pendingIndex}
        labels={["Move-in", "Move-out"]}
      />

      <div className="result-grid">
        <div>
          <h3 className="col-title">Findings</h3>
          <Findings findings={spot.state.findings} active={active} setActive={setActive} />
        </div>
        <div>
          <h3 className="col-title">What the agent did</h3>
          <Trace steps={spot.state.trace} />
          {reg.inliers && (
            <p className="reg-note mono">
              {reg.inliers} matched points · {Math.round((reg.overlap ?? 0) * 100)}% overlap · {reg.ms} ms
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
