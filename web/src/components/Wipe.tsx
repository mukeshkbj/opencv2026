import { useCallback, useRef, useState } from "react";

export interface Mark {
  box: [number, number, number, number];
  verdict: string;
  tag?: string;
}

const VERDICT_TEXT: Record<string, string> = {
  changed: "Changed",
  lighting: "Lighting only",
  unchanged: "No change",
  uncertain: "Can't judge",
  pending: "Checking",
};

export const verdictText = (v: string) => VERDICT_TEXT[v] ?? v;

export function Marks({ marks, active }: { marks: Mark[]; active?: number | null }) {
  return (
    <>
      {marks.map((m, i) => (
        <div
          key={i}
          className="mark"
          data-v={m.verdict}
          data-active={active === i || undefined}
          data-right={m.box[0] + m.box[2] / 2 > 0.6 || undefined}
          data-inside={m.box[1] < 0.08 || undefined}
          style={{
            left: `${m.box[0] * 100}%`,
            top: `${m.box[1] * 100}%`,
            width: `${m.box[2] * 100}%`,
            height: `${m.box[3] * 100}%`,
          }}
        >
          {m.tag && <span className="mark-tag">{m.tag}</span>}
        </div>
      ))}
    </>
  );
}

interface WipeProps {
  before: string;
  after: string;
  ratio: number;
  marks?: Mark[];
  heat?: string;
  showHeat?: boolean;
  active?: number | null;
  labels?: [string, string];
}

export default function Wipe({ before, after, ratio, marks = [], heat, showHeat, active, labels = ["Before", "After"] }: WipeProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState(0.5);
  const [loupe, setLoupe] = useState<{ x: number; y: number } | null>(null);

  const fromEvent = useCallback((clientX: number, clientY: number) => {
    const r = ref.current!.getBoundingClientRect();
    return { x: Math.min(1, Math.max(0, (clientX - r.left) / r.width)), y: Math.min(1, Math.max(0, (clientY - r.top) / r.height)) };
  }, []);

  const onPointer = (e: React.PointerEvent) => {
    const p = fromEvent(e.clientX, e.clientY);
    if (e.buttons === 1 || e.pointerType !== "mouse") setPos(p.x);
    if (e.pointerType === "mouse") setLoupe(p);
  };

  const onKey = (e: React.KeyboardEvent) => {
    const step = e.shiftKey ? 0.1 : 0.02;
    if (e.key === "ArrowLeft") setPos((p) => Math.max(0, p - step));
    else if (e.key === "ArrowRight") setPos((p) => Math.min(1, p + step));
    else return;
    e.preventDefault();
  };

  const zoom = 2.6;
  return (
    <div
      ref={ref}
      className="wipe"
      style={{ aspectRatio: ratio }}
      onPointerDown={(e) => {
        (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
        setPos(fromEvent(e.clientX, e.clientY).x);
      }}
      onPointerMove={onPointer}
      onPointerLeave={() => setLoupe(null)}
    >
      <img src={after} alt={`${labels[1]} photo`} draggable={false} />
      <div className="wipe-before" style={{ clipPath: `inset(0 ${(1 - pos) * 100}% 0 0)` }}>
        <img src={before} alt={`${labels[0]} photo`} draggable={false} />
      </div>
      {heat && <img className="wipe-heat" src={heat} alt="" data-on={showHeat || undefined} draggable={false} />}
      <Marks marks={marks} active={active} />
      <span className="wipe-label" data-side="l">{labels[0]}</span>
      <span className="wipe-label" data-side="r">{labels[1]}</span>
      <div
        className="wipe-handle"
        style={{ left: `${pos * 100}%` }}
        role="slider"
        tabIndex={0}
        aria-label="Compare before and after"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(pos * 100)}
        onKeyDown={onKey}
      >
        <span />
      </div>
      {loupe && (
        <div
          className="loupe"
          aria-hidden="true"
          style={{
            left: `${loupe.x * 100}%`,
            top: `${loupe.y * 100}%`,
            backgroundImage: `url(${loupe.x < pos ? before : after})`,
            backgroundSize: `${zoom * 100}% auto`,
            backgroundPosition: `${loupe.x * 100}% ${loupe.y * 100}%`,
          }}
        />
      )}
    </div>
  );
}
