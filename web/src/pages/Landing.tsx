import gsap from "gsap";
import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { navigate, TopBar } from "../App";
import GhostLock from "../components/GhostLock";
import Wipe, { type Mark } from "../components/Wipe";

interface HeroSpot {
  w: number;
  h: number;
  findings: { box: [number, number, number, number]; verdict: string; kind: string }[];
}
type HeroData = Record<"room" | "desk" | "car", HeroSpot>;

const TAGS: Record<string, string[]> = {
  room: ["Floor scuff · new", "Wall stain · new", "Shadow · ignored"],
  desk: ["Item missing", "Coffee ring · new", "Shadow · ignored"],
};

function marksFor(spot: HeroSpot, name: keyof typeof TAGS): Mark[] {
  return spot.findings.map((f, i) => ({ box: f.box, verdict: f.verdict, tag: TAGS[name][i] }));
}

function useStartSample() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const start = async () => {
    setBusy(true);
    setError("");
    try {
      const check = await api.sample();
      navigate(`/check/${check.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };
  return { busy, error, start };
}

function useReveal() {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const items = ref.current!.querySelectorAll<HTMLElement>("[data-reveal]");
    gsap.set(items, { y: 24, opacity: 0 });
    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (!e.isIntersecting) return;
          gsap.to(e.target, { y: 0, opacity: 1, duration: 0.9, ease: "expo.out" });
          io.unobserve(e.target);
        }),
      { rootMargin: "0px 0px -10% 0px" },
    );
    items.forEach((i) => io.observe(i));
    return () => io.disconnect();
  }, []);
  return ref;
}

export default function Landing() {
  const [hero, setHero] = useState<HeroData | null>(null);
  const sample = useStartSample();
  const main = useReveal();

  useEffect(() => {
    fetch("/hero/hero.json").then((r) => r.json()).then(setHero);
  }, []);

  return (
    <>
      <TopBar>
        <a className="btn" href="#how">How it works</a>
        <button className="btn btn-primary" onClick={sample.start} disabled={sample.busy}>
          {sample.busy ? "Opening…" : "Try the sample"}
        </button>
      </TopBar>

      <main ref={main}>
        <section className="hero">
          <div className="hero-copy">
            <h1 className="hero-title">
              Take it <em>twice.</em>
            </h1>
            <div className="hero-side">
              <a className="hero-hook" href="#hook">
                <b>$440</b> billed by an AI scanner for a one-inch scuff. The renter had only a phone.
              </a>
              <p className="hero-lede">
                Photograph your apartment or rental car when you get it. Photograph it again when you give it back. Twice walks you to
                the exact same spot, finds what really changed, and signs the proof.
              </p>
              <div className="hero-cta">
                <button className="btn btn-signal" onClick={sample.start} disabled={sample.busy}>
                  {sample.busy ? "Opening the sample…" : "Try the sample check"}
                  <span className="arrow" aria-hidden="true">→</span>
                </button>
                <button className="btn" onClick={() => api.createCheck("My move-in").then((c) => navigate(`/check/${c.id}`))}>
                  Start my own
                </button>
              </div>
              {sample.error && <p className="form-error" role="alert">{sample.error}. Is the server running?</p>}
            </div>
          </div>

          <figure className="plate hero-plate">
            {hero ? (
              <GhostLock
                before="/hero/room-a.jpg"
                after="/hero/room-b.jpg"
                ratio={hero.room.w / hero.room.h}
                marks={marksFor(hero.room, "room")}
              />
            ) : (
              <div className="ghostlock skeleton" style={{ aspectRatio: 1571 / 880 }} />
            )}
            <figcaption>
              <span className="label">Move-out photo, locked onto the move-in photo</span>
              <span className="label">Difference view: only real changes stay bright</span>
            </figcaption>
          </figure>
        </section>

        <section className="hook" id="hook">
          <div className="hook-figure" data-reveal>
            <span className="hook-number">$440</span>
            <span className="label">for a one-inch scuff on a wheel</span>
          </div>
          <div className="hook-copy" data-reveal>
            <h2>Rental companies scan with AI. Renters have a phone.</h2>
            <p>
              Hertz uses AI scanners at airport returns. One renter got a $440 bill for a one-inch wheel scuff, minutes after the return.
              A House subcommittee chair wrote that Hertz is the only rental company that bills from these scans without human review.
            </p>
            <p>
              Apartments work the same way. The landlord keeps detailed move-out photos. Most renters keep a few blurry ones and hope.
            </p>
            <p className="source">
              Sources: <a href="https://www.thedrive.com/news/this-is-what-happens-when-hertzs-ai-scanner-finds-damage-on-your-rental" target="_blank" rel="noreferrer">The Drive ↗</a> 
              <a href="https://oversight.house.gov/release/mace-investigates-use-of-artificial-intelligence-for-car-rental-damage-assessments" target="_blank" rel="noreferrer">House Oversight ↗</a>
              <a href="https://www.repairerdrivennews.com/2025/08/25/subcommittee-requests-briefing-from-hertz-on-ai-scanning-technology/" target="_blank" rel="noreferrer">Repairer Driven News ↗</a>
            </p>
          </div>
          <div className="receipt" data-reveal aria-label="The $440 bill, itemised">
            <div className="receipt-row"><span>Damage</span><span>$250.00</span></div>
            <div className="receipt-row"><span>Processing</span><span>$125.00</span></div>
            <div className="receipt-row"><span>Administrative fee</span><span>$65.00</span></div>
            <div className="receipt-row total"><span>Total</span><span>$440.00</span></div>
            <p className="receipt-note">Sent minutes after the return</p>
          </div>
        </section>

        <section className="how" id="how">
          <header className="section-head" data-reveal>
            <h2>Three visits. Two of them take a minute.</h2>
          </header>
          <ol className="steps">
            <li className="step" data-reveal>
              <div className="step-img">
                <img src="/hero/room-a.jpg" alt="" loading="lazy" />
                <div className="qc">
                  <span className="chip" data-ok>Sharp</span>
                  <span className="chip" data-ok>Light</span>
                  <span className="chip" data-ok>Detail</span>
                </div>
              </div>
              <h3><span className="step-n">1</span>Move in</h3>
              <p>Shoot three to six spots. The shutter waits until each photo is sharp, bright and detailed enough to compare later. Then Twice seals the set with a signature and a timestamp.</p>
            </li>
            <li className="step" data-reveal>
              <div className="step-img ghost-demo">
                <img src="/hero/car-a.jpg" alt="" loading="lazy" />
                <img className="ghost-layer" src="/hero/car-b.jpg" alt="" loading="lazy" />
                <span className="ghost-hint">Pan left</span>
              </div>
              <h3><span className="step-n">2</span>Move out</h3>
              <p>A ghost of each first photo floats over your camera. Line it up and Twice shoots on its own. Same angle, same distance, months later.</p>
            </li>
            <li className="step" data-reveal>
              <div className="step-img exhibit">
                <img className="exhibit-photo" src="/hero/room-b.jpg" alt="" loading="lazy" />
                <div className="exhibit-card">
                  <span className="label">Exhibit A · Wall stain</span>
                  <span className="mono">sha256 c0c9…3769</span>
                  <span className="mono">Signature verified</span>
                </div>
              </div>
              <h3><span className="step-n">3</span>The proof</h3>
              <p>You get a report with every change, every ruled-out shadow and every original photo. Anyone can check that nothing was edited after it was signed.</p>
            </li>
          </ol>
        </section>

        <section className="restraint">
          <div className="restraint-copy" data-reveal>
            <h2>It knows a shadow from a stain.</h2>
            <p>
              A false accusation is worse than none. Twice sorts every difference into one of three answers and shows you why.
            </p>
            <ul className="legend">
              <li><span className="chip" data-v="changed">Changed</span> New marks, stains, scratches, missing things.</li>
              <li><span className="chip" data-v="lighting">Lighting only</span> Shadows, lamps and sun. The texture underneath is the same.</li>
              <li><span className="chip" data-v="uncertain">Can't judge</span> Twice says so, and leaves it to a person.</li>
            </ul>
            <div className="trace-snippet" aria-label="Agent trace for a reflection on the rental car">
              <span className="label">When it is unsure, it asks for one more photo</span>
              <code>glare_check   +10% near-white pixels → ask for a step to the side</code>
              <code>parallax      reflection moved with the camera</code>
              <code>decision      ruled out: glare, not damage</code>
            </div>
          </div>
          <figure className="plate" data-reveal>
            {hero && (
              <Wipe
                before="/hero/desk-a.jpg"
                after="/hero/desk-b.jpg"
                ratio={hero.desk.w / hero.desk.h}
                marks={marksFor(hero.desk, "desk")}
                labels={["Move-in", "Move-out"]}
              />
            )}
            <figcaption>
              <span className="label">Drag to compare. Hover to inspect with the loupe.</span>
            </figcaption>
          </figure>
        </section>

        <section className="engine">
          <header className="section-head" data-reveal>
            <h2>Geometry decides. Language only labels.</h2>
            <p>Every verdict comes from measurements you can read in the report. The language model names what changed. It cannot delete a finding.</p>
          </header>
          <ol className="pipeline" data-reveal>
            <li><span className="label">Register</span><code>SIFT · USAC MAGSAC homography</code><p>Matches thousands of points and warps the new photo onto the old one.</p></li>
            <li><span className="label">Refine</span><code>DIS optical flow, clamped</code><p>Corrects the last few pixels a handheld phone leaves behind.</p></li>
            <li><span className="label">Compare</span><code>Shift-tolerant structure + colour</code><p>Ignores blur, exposure and sub-pixel jitter. Keeps new texture.</p></li>
            <li><span className="label">Decide</span><code>Agent · NanoDet on dnn ENGINE_NEW</code><p>Rules out light, names missing objects, asks for a parallax shot or a close-up when unsure.</p></li>
            <li><span className="label">Sign</span><code>SHA-256 · AWS KMS, ECDSA P-256 (Ed25519 when run locally)</code><p>Seals the photos and the findings. Any edit breaks the signature.</p></li>
          </ol>
          <dl className="stats" data-reveal>
            <div><dt>Damage found</dt><dd>90%</dd><small>170 synthetic pairs</small></div>
            <div><dt>Flags that are real</dt><dd>99%</dd><small>170 synthetic pairs</small></div>
            <div><dt>Lighting false alarms</dt><dd>3%</dd><small>shadow and lamp pairs</small></div>
            <div><dt>Real photos, false alarms</dt><dd>2 of 22</dd><small>18 more sent back for a retake</small></div>
            <div><dt>Time to compare</dt><dd>0.9 s</dd><small>median, desktop CPU</small></div>
          </dl>
          <p className="stats-note">The synthetic benchmark runs the full agent loop on photo pairs with known damage, camera moves, exposure, colour, shadow and glare, including the follow-up shots it asks for. The real photos are the Oxford affine sequences: unchanged scenes, so they measure false alarms only. Method and failure cases are in the technical report.</p>
        </section>

        <section className="closer" data-reveal>
          <h2>Your next move‑out starts with today's photos.</h2>
          <div className="hero-cta">
            <button className="btn btn-signal" onClick={sample.start} disabled={sample.busy}>
              Try the sample check <span className="arrow" aria-hidden="true">→</span>
            </button>
            <button className="btn" onClick={() => api.createCheck("My move-in").then((c) => navigate(`/check/${c.id}`))}>
              Start my own
            </button>
          </div>
        </section>
      </main>

      <footer className="footer">
        <span>Built with OpenCV 5 for AWS, for the OpenCV AI Competition 2026.</span>
        <span>
          Sample photos: Sunny Room in old Apartment (CC BY 2.0), Top Workspace Office (CC0), 1970 AMC Hornet SST (CC BY 4.0), via Wikimedia Commons. Damage in the samples is synthetic.
        </span>
      </footer>
    </>
  );
}
