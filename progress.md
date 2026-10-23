# Progress

Target: OpenCV AI Competition 2026 (Devpost). Deadline: 2026-10-26 23:45 PT.

## Hard requirements (from the rules page)
- OpenCV 5 does substantive image or video analysis.
- A meaningful component runs on AWS.
- Technical report, judge-accessible repo, pinned dependencies, build/deploy/test instructions.
- Architecture diagram (OpenCV 5 + AWS + agent components).
- Working web endpoint or live demo. Video of 5 minutes or less.
- Evaluation evidence, including failure cases.

Rubric: technical 30, innovation 20, impact 20, UX 10, docs 10, cloud/responsible ops 10.
Special awards: Agentic Vision (vision output must change the next agent action), Best Use of COOL.

## Idea
Twice: take the same photo twice, see what really changed, sign the proof. Renter-side evidence for
apartments and rental cars. Spec: docs/spec.md. Persona critique: docs/critique-round1.md.

## Phases
- [x] 1. Research (docs/research.md)
- [x] 2. Idea candidates + persona critique (docs/ideas.md, docs/critique-round1.md)
- [x] 3. CV pipeline + agent (server/twice). Synthetic benchmark: recall 0.91, precision 0.84, 0.35 FP/pair.
- [x] 4. Web app (web/). Sample flow verified in the browser at 1440 px and 390 px: landing, three spots,
      parallax follow-ups, signed report, verification stamp.
- [x] 4b. OpenCV 5 DNN: NanoDet on ENGINE_NEW as agent `object_check` (median 16.3 ms vs 56.5 ms classic, server/eval/engines.py).
- [x] 5. AWS deploy kit: Dockerfile, deploy/template.yaml (cfn-lint clean), deploy.sh. Docker build and run verified locally. Not deployed (no credentials).
- [x] 6. Evaluation: server/eval/bench.py (170 pairs, stress, ablations), docs/evaluation.md, docs/eval/.
- [x] 6b. Diagrams: docs/diagrams/architecture.png, agent-loop.png.
- [x] 6e. Critique round 2 (docs/critique-round2.md) applied: freeze after report seal, seals checked against current
      state, sources fixed (The Drive, House Oversight), engine timing script (16.3 vs 56.5 ms), LLM cannot change
      verdicts, S3 uses bucket KMS key, concurrency cap + budget, car-first sample, keep-this-link card.
- [x] 6f. Engine hill-climb from the eval (agent-level bench server/eval/agent_bench.py):
      precision 0.972 -> 0.993, recall 0.852 -> 0.901, lighting false alarms 0.30 -> 0.033 of pairs.
- [ ] 6g. Full bench re-run in progress; then refresh docs/evaluation.md, report section 7, README, landing stats.
- [x] 6c. README, docs/report.md (eval section placeholder EVAL_SUMMARY), docs/video-script.md.
- [x] 6d. Verification now checks photos against signed manifests; report seal links to move-in seal. 6 tests pass.
- [ ] 7. Hill-climb: dark theme check, second persona critique on the built product, code-deslop pass.

## How to run locally
- API: `cd server && ../.venv/Scripts/python.exe -m uvicorn twice.app:app --reload --port 8000` (TWICE_DATA defaults to local store).
- Web: `cd web && npx vite --port 5288` (proxies /api to 8000). Port 5173 is used by another app.
- Tests: `cd server && ../.venv/Scripts/python.exe -m pytest -q tests` (8 pass).
- Bench: `cd server && python eval/bench.py` (about 15 min), then `python eval/agent_bench.py` (about 1 min).

## Surprises
- Vite can serve a module caught between two quick file writes; the browser then keeps that stale `?t=` URL. Touch the file to rebuild.
- The uvicorn `--reload` worker served old code for a while. The API now runs without `--reload`; restart it after server edits.
- On Windows, killing the uvicorn `--reload` parent left its worker holding port 8000 and serving stale code. Check `netstat -ano | grep :8000` after restarts.

## Environment notes
- No AWS CLI or credentials on this machine. `envsync` is not installed at ~/.local/bin.
- Global CLAUDE.md default path `/Users/hridyaagrawal/honey` does not exist on this Windows machine; work stays in this repo.
- RTX 4070 Ti, Docker 27, Node 24, Python 3.14, uv available.
