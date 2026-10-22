import { useEffect, useState } from "react";
import { api, fileUrl, type Check, type Spot, type Verification } from "../api";
import { TopBar } from "../App";
import { Marks, verdictText, type Mark } from "../components/Wipe";

const WORK_SIDE = 1024;

const when = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

function marksOf(spot: Spot): { marks: Mark[]; ratio: number } {
  const s = Math.min(1, WORK_SIDE / Math.max(spot.before.w, spot.before.h));
  const w = Math.round(spot.before.w * s);
  const h = Math.round(spot.before.h * s);
  return {
    ratio: w / h,
    marks: spot.state.findings
      .filter((f) => f.verdict !== "unchanged")
      .map((f, i) => ({ box: [f.box[0] / w, f.box[1] / h, f.box[2] / w, f.box[3] / h], verdict: f.verdict, tag: `${i + 1}` })),
  };
}

function download(name: string, data: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}

export default function ReportPage({ id }: { id: string }) {
  const [check, setCheck] = useState<Check | null>(null);
  const [verify, setVerify] = useState<Verification | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.check(id).then(setCheck).catch((e) => setError(e.message));
    api.verify(id).then(setVerify).catch(() => undefined);
  }, [id]);

  if (error) {
    return (
      <>
        <TopBar />
        <div className="page-msg">
          <h1>We couldn't open this report.</h1>
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
        <div className="report"><div className="skeleton" style={{ height: 600 }} /></div>
      </>
    );
  }

  const before = check.seals.find((s) => s.phase === "before");
  const final = check.seals.find((s) => s.phase === "report");
  const all = check.spots.flatMap((s) => s.state.findings);
  const changed = all.filter((f) => f.verdict === "changed").length;
  const ruled = all.filter((f) => f.verdict === "lighting" || f.verdict === "unchanged").length;
  const unsure = all.filter((f) => f.verdict === "uncertain").length;
  const share = `${location.origin}${location.pathname}#/report/${check.id}`;

  return (
    <>
      <TopBar>
        <a className="btn" href={`#/check/${check.id}`}>Back to the check</a>
        <button className="btn btn-primary" onClick={() => window.print()}>Save as PDF</button>
      </TopBar>
      <article className="report">
        <header className="report-head">
          <div>
            <span className="label">Condition report</span>
            <h1>{check.name}</h1>
            <p className="report-dates mono">
              Move-in sealed {before ? when(before.manifest.signed_at as string) : "—"} · Report signed {final ? when(final.manifest.signed_at as string) : "—"}
            </p>
          </div>
          <div className="stamp" data-ok={verify?.ok ?? undefined} data-bad={verify && !verify.ok ? true : undefined}>
            <span>{verify ? (verify.ok ? "Verified" : "Altered") : "Checking"}</span>
            <small className="mono">{verify ? `${verify.files.length} photos · ${verify.seals.length} signatures` : "…"}</small>
          </div>
        </header>

        <dl className="report-summary">
          <div><dt>Changed</dt><dd data-v="changed">{changed}</dd></div>
          <div><dt>Ruled out</dt><dd>{ruled}</dd></div>
          <div><dt>Can't judge</dt><dd>{unsure}</dd></div>
          <div><dt>Spots</dt><dd>{check.spots.length}</dd></div>
        </dl>

        {check.spots.map((spot, n) => {
          const { marks, ratio } = marksOf(spot);
          const shown = spot.state.findings.filter((f) => f.verdict !== "unchanged");
          const photos = [
            { role: "Move-in", p: spot.before },
            ...(spot.after ? [{ role: "Move-out", p: spot.after }] : []),
            ...spot.followups.map((f) => ({ role: f.kind === "parallax" ? "Side-step" : "Close-up", p: f })),
          ];
          return (
            <section className="exhibit-sec" key={spot.id}>
              <header className="exhibit-head">
                <span className="label">Exhibit {String.fromCharCode(65 + n)}</span>
                <h2>{spot.label}</h2>
              </header>
              {spot.after ? (
                <div className="pair">
                  <figure>
                    <div className="pair-img" style={{ aspectRatio: ratio }}>
                      <img src={fileUrl(check.id, `${spot.id}-view-before.jpg`)} alt={`${spot.label}, move-in`} />
                    </div>
                    <figcaption className="label">Move-in</figcaption>
                  </figure>
                  <figure>
                    <div className="pair-img" style={{ aspectRatio: ratio }}>
                      <img src={fileUrl(check.id, `${spot.id}-view-after.jpg`)} alt={`${spot.label}, move-out, aligned to move-in`} />
                      <Marks marks={marks} />
                    </div>
                    <figcaption className="label">Move-out, aligned</figcaption>
                  </figure>
                </div>
              ) : (
                <p className="empty">No move-out photo for this spot.</p>
              )}
              {shown.length > 0 && (
                <table className="ftable">
                  <thead>
                    <tr><th>#</th><th>Result</th><th>What</th><th>Evidence</th></tr>
                  </thead>
                  <tbody>
                    {shown.map((f, i) => (
                      <tr key={f.id}>
                        <td className="mono">{i + 1}</td>
                        <td><span className="chip" data-v={f.verdict}>{verdictText(f.verdict)}</span></td>
                        <td>{f.caption || (f.verdict === "lighting" ? (f.kind === "glare" ? "Reflection" : "Shadow or light change") : f.kind === "object" ? "Object added, moved or removed" : "Surface change")}</td>
                        <td className="ev">{f.evidence.join(". ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <ul className="hashes">
                {photos.map(({ role, p }) => {
                  const ok = verify?.files.find((f) => f.sha256 === p.sha256)?.ok;
                  return (
                    <li key={p.sha256} className="mono">
                      <span className="hash-role">{role}</span>
                      <span>{when(p.at)}</span>
                      <span className="hash">{p.sha256}</span>
                      <span data-ok={ok ?? undefined}>{ok === undefined ? "" : ok ? "matches" : "ALTERED"}</span>
                    </li>
                  );
                })}
              </ul>
            </section>
          );
        })}

        <section className="sig">
          <h2>Signatures</h2>
          {check.seals.map((s) => {
            const v = verify?.seals.find((x) => x.digest === s.digest);
            return (
              <div className="sig-row" key={s.phase}>
                <span className="label">{s.phase === "before" ? "Move-in set" : "Full report"}</span>
                <code className="mono">digest {s.digest}</code>
                <code className="mono sig-value">{s.algorithm} {s.signature}</code>
                <span className="mono" data-ok={v ? v.digest_ok && v.signature_ok : undefined}>
                  {v ? (v.digest_ok && v.signature_ok ? "signature valid" : "signature INVALID") : "checking"}
                </span>
              </div>
            );
          })}
          {verify && (
            <details className="pubkey">
              <summary>Public key ({verify.algorithm})</summary>
              <pre className="mono">{verify.public_key}</pre>
            </details>
          )}
          <div className="report-actions">
            <button className="btn" onClick={() => download(`twice-${check.id}.json`, { check, verification: verify })}>Download evidence file</button>
            <button
              className="btn"
              onClick={() => navigator.clipboard.writeText(share).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800); })}
            >
              {copied ? "Link copied" : "Copy share link"}
            </button>
          </div>
        </section>

        <section className="limits">
          <h2>What this report cannot prove</h2>
          <ul>
            <li>It covers only the spots that were photographed. It says nothing about anything outside them.</li>
            <li>Times come from the Twice server clock at upload, not from the camera.</li>
            <li>The signature proves the photos and findings did not change after signing. It does not prove a photo shows what it claims to show.</li>
            <li>Findings are measurements, not legal conclusions. A person should review every "Changed" and "Can't judge" item.</li>
            {check.sample && <li>This is a sample check. Its photos are real, but the damage, lighting and camera moves were added by software.</li>}
          </ul>
        </section>
      </article>
    </>
  );
}
