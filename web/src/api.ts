export type Verdict = "pending" | "changed" | "lighting" | "uncertain" | "unchanged";

export interface Quality {
  sharpness: number;
  brightness: number;
  clipped: number;
  features: number;
  ok: boolean;
  issue: "too_dark" | "too_bright" | "blurry" | "featureless" | null;
}

export interface Photo {
  key: string;
  sha256: string;
  at: string;
  w: number;
  h: number;
}

export interface Finding {
  id: string;
  box: [number, number, number, number];
  metrics: Record<string, number | boolean>;
  verdict: Verdict;
  kind: string;
  evidence: string[];
  caption: string;
}

export interface FollowupRequest {
  id: string;
  finding: string;
  kind: "parallax" | "closeup";
  prompt: string;
  box: [number, number, number, number];
}

export interface TraceStep {
  t: number;
  tool: string;
  result: string;
  decision: string;
}

export interface SpotState {
  findings: Finding[];
  trace: TraceStep[];
  pending: FollowupRequest | null;
  followups_used: number;
  status: "new" | "retake" | "needs_followup" | "done";
  registration: { inliers?: number; overlap?: number; ms?: number };
}

export interface Spot {
  id: string;
  label: string;
  before: Photo & { quality: Quality };
  after: Photo | null;
  followups: (Photo & { kind: string })[];
  state: SpotState;
  sample?: Record<string, string>;
}

export interface Seal {
  phase: "before" | "report";
  manifest: Record<string, unknown>;
  digest: string;
  signature: string;
  algorithm: string;
}

export interface Check {
  id: string;
  name: string;
  created_at: string;
  spots: Spot[];
  seals: Seal[];
  sample?: string;
}

export interface Guidance {
  aligned: boolean;
  score: number;
  instruction: string;
  quad: [number, number][] | null;
  dx: number;
  dy: number;
  scale: number;
  roll: number;
  quality: Partial<Quality>;
  ms: number;
}

export interface Verification {
  ok: boolean;
  algorithm: string;
  public_key: string;
  fingerprint: string;
  files: { spot: string; role: string; sha256: string; ok: boolean }[];
  seals: { phase: string; digest: string; digest_ok: boolean; signature_ok: boolean }[];
}

export interface Health {
  opencv: string;
  signer: string;
  captioner: string;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

function form(file: Blob, name = "photo.jpg"): FormData {
  const f = new FormData();
  f.append("file", file, name);
  return f;
}

const post = <T>(path: string, body?: BodyInit, headers?: HeadersInit) =>
  call<T>(path, { method: "POST", body, headers });

export const api = {
  health: () => call<Health>("/health"),
  createCheck: (name: string) =>
    post<Check>("/checks", JSON.stringify({ name }), { "Content-Type": "application/json" }),
  sample: () => post<Check>("/samples/apartment"),
  check: (id: string) => call<Check>(`/checks/${id}`),
  addSpot: (id: string, file: Blob, label: string) =>
    post<Spot>(`/checks/${id}/spots?label=${encodeURIComponent(label)}`, form(file)),
  seal: (id: string) => post<Seal>(`/checks/${id}/seal`),
  quality: (frame: Blob) => post<Quality>("/quality", frame, { "Content-Type": "image/jpeg" }),
  guide: (id: string, sid: string, frame: Blob) =>
    post<Guidance>(`/checks/${id}/spots/${sid}/guide`, frame, { "Content-Type": "image/jpeg" }),
  after: (id: string, sid: string, file: Blob) => post<Spot>(`/checks/${id}/spots/${sid}/after`, form(file)),
  followup: (id: string, sid: string, file: Blob) => post<Spot>(`/checks/${id}/spots/${sid}/followup`, form(file)),
  sampleShot: (id: string, sid: string) => post<Spot>(`/checks/${id}/spots/${sid}/sample-shot`),
  report: (id: string) => post<Check>(`/checks/${id}/report`),
  verify: (id: string) => call<Verification>(`/checks/${id}/verify`),
};

export const fileUrl = (checkId: string, name: string) => `/api/checks/${checkId}/files/${name}`;
export const photoUrl = (checkId: string, p: Photo) => fileUrl(checkId, p.key.split("/").pop()!);
