import { useCallback, useEffect, useRef, useState } from "react";
import type { Guidance, Quality } from "../api";

type Mode = "before" | "guide" | "followup";

interface Props {
  mode: Mode;
  ghost?: string;
  prompt?: string;
  busy?: boolean;
  quality: (frame: Blob) => Promise<Quality>;
  guide?: (frame: Blob) => Promise<Guidance>;
  onCapture: (photo: Blob) => void;
}

const ISSUE_TEXT: Record<string, string> = {
  too_dark: "More light, please",
  too_bright: "Too much glare",
  blurry: "Hold steady",
  featureless: "Include an edge or a corner",
};

/** CSS matrix3d that maps the box (0,0)-(w,h) onto the quad tl, tr, br, bl. */
function quadTransform(w: number, h: number, q: [number, number][]): string {
  const [[x0, y0], [x1, y1], [x2, y2], [x3, y3]] = q;
  const dx1 = x1 - x2, dx2 = x3 - x2, dx3 = x0 - x1 + x2 - x3;
  const dy1 = y1 - y2, dy2 = y3 - y2, dy3 = y0 - y1 + y2 - y3;
  const den = dx1 * dy2 - dx2 * dy1;
  const g = (dx3 * dy2 - dx2 * dy3) / den;
  const hh = (dx1 * dy3 - dx3 * dy1) / den;
  const a = x1 - x0 + g * x1, b = x3 - x0 + hh * x3;
  const d = y1 - y0 + g * y1, e = y3 - y0 + hh * y3;
  const m = [a / w, d / w, 0, g / w, b / h, e / h, 0, hh / h, 0, 0, 1, 0, x0, y0, 0, 1];
  return `matrix3d(${m.map((v) => +v.toFixed(8)).join(",")})`;
}

async function grab(video: HTMLVideoElement, maxSide: number, quality = 0.72): Promise<Blob> {
  const s = Math.min(1, maxSide / Math.max(video.videoWidth, video.videoHeight));
  const c = document.createElement("canvas");
  c.width = Math.round(video.videoWidth * s);
  c.height = Math.round(video.videoHeight * s);
  c.getContext("2d")!.drawImage(video, 0, 0, c.width, c.height);
  return new Promise((res) => c.toBlob((b) => res(b!), "image/jpeg", quality));
}

async function shrink(file: Blob, maxSide = 2400): Promise<Blob> {
  const bmp = await createImageBitmap(file, { imageOrientation: "from-image" });
  const s = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
  const c = document.createElement("canvas");
  c.width = Math.round(bmp.width * s);
  c.height = Math.round(bmp.height * s);
  c.getContext("2d")!.drawImage(bmp, 0, 0, c.width, c.height);
  bmp.close();
  return new Promise((res) => c.toBlob((b) => res(b!), "image/jpeg", 0.92));
}

export default function Camera({ mode, ghost, prompt, busy, quality, guide, onCapture }: Props) {
  const video = useRef<HTMLVideoElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"starting" | "live" | "denied">(() => (navigator.mediaDevices ? "starting" : "denied"));
  const [aspect, setAspect] = useState(4 / 3);
  const [q, setQ] = useState<Partial<Quality> | null>(null);
  const [g, setG] = useState<Guidance | null>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [flash, setFlash] = useState(false);
  const lockRun = useRef(0);
  const captured = useRef(false);

  useEffect(() => {
    let stream: MediaStream | null = null;
    let cancelled = false;
    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: "environment", width: { ideal: 1920 }, height: { ideal: 1440 } }, audio: false })
      .then((s) => {
        if (cancelled) return s.getTracks().forEach((t) => t.stop());
        stream = s;
        const v = video.current!;
        v.srcObject = s;
        v.onloadedmetadata = () => {
          setAspect(v.videoWidth / v.videoHeight);
          setState("live");
        };
      })
      .catch(() => setState("denied"));
    return () => {
      cancelled = true;
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  useEffect(() => {
    const el = stage.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setSize({ w: e.contentRect.width, h: e.contentRect.height }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const shoot = useCallback(async () => {
    const v = video.current;
    if (!v || captured.current) return;
    captured.current = true;
    setFlash(true);
    setTimeout(() => setFlash(false), 220);
    onCapture(await grab(v, 2400, 0.92));
  }, [onCapture]);

  useEffect(() => {
    if (busy) return;
    captured.current = false;
    lockRun.current = 0;
  }, [busy, mode, ghost, prompt]);

  useEffect(() => {
    if (state !== "live" || busy) return;
    let stop = false;
    const loop = async () => {
      while (!stop) {
        const v = video.current;
        if (!v || v.readyState < 2) {
          await new Promise((r) => setTimeout(r, 200));
          continue;
        }
        try {
          const frame = await grab(v, 480);
          if (mode === "guide" && guide) {
            const res = await guide(frame);
            if (stop) break;
            setG(res);
            setQ(res.quality);
            lockRun.current = res.aligned ? lockRun.current + 1 : 0;
            if (lockRun.current >= 3) {
              await shoot();
              break;
            }
          } else {
            const res = await quality(frame);
            if (stop) break;
            setQ(res);
            await new Promise((r) => setTimeout(r, 350));
          }
        } catch {
          await new Promise((r) => setTimeout(r, 800));
        }
      }
    };
    loop();
    return () => {
      stop = true;
    };
  }, [state, mode, busy, guide, quality, shoot]);

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) shrink(f).then(onCapture, () => onCapture(f));
    e.target.value = "";
  };

  const instruction =
    mode === "guide" ? g?.instruction ?? "Find the spot from your first visit" : q && !q.ok && q.issue ? ISSUE_TEXT[q.issue] : "Looks good";
  const ok = mode === "guide" ? g?.aligned : q?.ok;
  const quad = mode === "guide" && g?.quad && size.w ? (g.quad.map(([x, y]) => [x * size.w, y * size.h]) as [number, number][]) : null;

  return (
    <div className="camera" data-mode={mode}>
      <div ref={stage} className="cam-stage" style={{ aspectRatio: aspect, ["--aspect" as string]: aspect }} data-ok={ok || undefined}>
        <video ref={video} playsInline muted autoPlay aria-label="Live camera" />
        {state === "starting" && <div className="cam-msg">Starting the camera…</div>}
        {state === "denied" && (
          <div className="cam-msg">
            <p>No camera available here. You can upload a photo instead.</p>
          </div>
        )}
        {mode === "guide" && ghost && state === "live" && (
          <img
            className="cam-ghost"
            src={ghost}
            alt=""
            style={quad ? { width: size.w, height: size.h, transform: quadTransform(size.w, size.h, quad) } : { opacity: 0.35, width: size.w, height: size.h }}
          />
        )}
        {state === "live" && (
          <>
            <div className="cam-corners" aria-hidden="true">
              <i /><i /><i /><i />
            </div>
            <div className="cam-hud" aria-live="polite">
              <span className="cam-dot" data-ok={ok || undefined} />
              {busy ? "Analysing…" : prompt && mode === "followup" ? prompt : instruction}
            </div>
            {mode === "guide" && g && (
              <div className="cam-meter" aria-label={`Alignment ${Math.round(g.score * 100)} percent`}>
                <span style={{ width: `${g.score * 100}%` }} />
              </div>
            )}
          </>
        )}
        {flash && <div className="cam-flash" />}
      </div>

      <div className="cam-bar">
        {mode !== "guide" && q && (
          <div className="qc-row">
            <span className="chip" data-pass={(q.sharpness ?? 0) >= 60 || undefined}>Sharp</span>
            <span className="chip" data-pass={(q.brightness ?? 0) >= 45 && (q.brightness ?? 0) <= 225 || undefined}>Light</span>
            <span className="chip" data-pass={(q.features ?? 0) >= 80 || undefined}>Detail</span>
          </div>
        )}
        {mode === "guide" && <span className="cam-note">Line up the ghost. Twice shoots on its own when it locks.</span>}
        <div className="cam-actions">
          <label className="btn">
            Upload a photo
            <input type="file" accept="image/*" capture="environment" onChange={onFile} hidden />
          </label>
          {state === "live" && (
            <button className="shutter" onClick={shoot} disabled={busy} aria-label="Take photo">
              <span />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
