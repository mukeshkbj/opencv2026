import gsap from "gsap";
import { useEffect, useRef, useState } from "react";
import { Marks, type Mark } from "./Wipe";

const Reg = ({ className }: { className: string }) => (
  <svg className={`reg ${className}`} viewBox="0 0 22 22" aria-hidden="true">
    <g fill="none" stroke="currentColor" strokeWidth="1.2">
      <circle cx="11" cy="11" r="5.5" />
      <path d="M11 0v22M0 11h22" />
    </g>
  </svg>
);

const STEPS = ["Pan left", "Tilt up", "Move closer", "Hold still"];

interface Props {
  before: string;
  after: string;
  ratio: number;
  marks: Mark[];
}

export default function GhostLock({ before, after, ratio, marks }: Props) {
  const root = useRef<HTMLDivElement>(null);
  const [step, setStep] = useState(0);
  const [phase, setPhase] = useState<"seek" | "lock" | "read">("seek");

  useEffect(() => {
    const el = root.current!;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ctx = gsap.context(() => {
      const ghost = ".gl-ghost";
      if (reduce) {
        gsap.set(ghost, { xPercent: 0, yPercent: 0, rotation: 0, scale: 1 });
        setPhase("read");
        setStep(3);
        return;
      }
      const tl = gsap.timeline({ repeat: -1, repeatDelay: 0.4, defaults: { ease: "power2.inOut" } });
      tl.call(() => {
        setPhase("seek");
        setStep(0);
      })
        .set(ghost, { xPercent: 7, yPercent: -5, rotation: -3.2, scale: 0.9, opacity: 1 })
        .set(".gl-marks", { opacity: 0 })
        .set(".gl-diff", { opacity: 0.55 })
        .to(ghost, { xPercent: 2.5, yPercent: -4, rotation: -2, duration: 1.1 })
        .call(() => setStep(1))
        .to(ghost, { xPercent: 1.5, yPercent: -0.8, rotation: -1.2, scale: 0.94, duration: 1 })
        .call(() => setStep(2))
        .to(ghost, { xPercent: 0.4, yPercent: -0.2, rotation: -0.3, scale: 0.99, duration: 0.9 })
        .call(() => setStep(3))
        .to(ghost, { xPercent: 0, yPercent: 0, rotation: 0, scale: 1, duration: 0.45, ease: "expo.out" })
        .call(() => setPhase("lock"))
        .to(".gl-diff", { opacity: 1, duration: 0.35, ease: "power2.out" })
        .to(".gl-target", { scale: 1.6, opacity: 0, duration: 0.5, ease: "power2.out" }, "<")
        .set(".gl-target", { scale: 1, opacity: 1 }, ">")
        .to({}, { duration: 1.6 })
        .call(() => setPhase("read"))
        .to(".gl-diff", { opacity: 0, duration: 0.7, ease: "power1.inOut" })
        .to(".gl-marks", { opacity: 1, duration: 0.4 }, "-=0.2")
        .to({}, { duration: 4.2 })
        .to(".gl-marks", { opacity: 0, duration: 0.3 });
    }, el);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={root} className="ghostlock" data-phase={phase} style={{ aspectRatio: ratio }}>
      <img className="gl-base" src={before} alt="Move-in photo of a living room" />
      <div className="gl-diff">
        <img className="gl-ghost" src={after} alt="" />
      </div>
      <div className="gl-ghost gl-frame" aria-hidden="true">
        <Reg className="tl" />
        <Reg className="tr" />
        <Reg className="bl" />
        <Reg className="br" />
      </div>
      <div className="gl-targets" aria-hidden="true">
        {["tl", "tr", "bl", "br"].map((c) => (
          <Reg key={c} className={`gl-target ${c}`} />
        ))}
      </div>
      <div className="gl-marks">
        <Marks marks={marks} />
      </div>
      <div className="gl-hud" aria-live="polite">
        <span className="gl-dot" />
        <span>{phase === "read" ? "Compared" : phase === "lock" ? "Locked. Same spot." : STEPS[step]}</span>
      </div>
    </div>
  );
}
