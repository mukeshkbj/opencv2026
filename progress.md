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
- [x] 6h. Real-photo bench (server/eval/real_bench.py, Oxford affine sequences, nothing changes). New retake rule
      `_same_view` in vision.compare (scale 0.8 to 1.25, anisotropy below 1.3): pairs with a false "changed" 7 -> 2 of
      the judged pairs; 9 pairs now get a retake. Agent bench unchanged (recall 0.901, precision 0.993).
- [x] 6i. README evaluation paragraph, landing stats, video-script numbers refreshed with agent-level numbers.
- [x] 6g. docs/evaluation.md rewritten for three levels (agent, engine, real photos) and report section 7 filled.
- [x] 6j. Offline evidence bundle: GET /api/checks/{id}/bundle (photos, seals, key, verify.py = twice/offline_verify.py).
      Report button + key fingerprint. Test covers photo edit, finding edit, missing move-in seal, missing report.
- [x] 6k. Sonnet 5.5 review applied: _same_view checks the Jacobian at centre and corners, rejects mirror images,
      normalises for image size (tests/test_vision.py); bundle ships only signed photos; hash format checked.
- [x] 6l. agent_bench runs 5 RANSAC seeds (it was not reproducible before: exposure pair 3 flipped between runs).
      Pooled: recall 0.901, precision 0.993, no-change 0.033, lighting 0.027 (0.017 to 0.033). Real: 22 judged, 2 false.
- [x] 6m. Engine bench re-run for the corner rule; section 5 stress and latency tables refreshed.
- [x] 6n. Demo recording docs/img/demo.mp4 (46 s) and docs/img/glare.gif in the README; fresh docs/img/report.png.
- [x] 6o. Critique round 3 (docs/critique-round3.md): Hertz claims checked against The Drive and the subcommittee
      letter, OpenCV 5 scope stated, numbers labelled, Can't-judge next step, mobile overflow and duplicate-key fixes,
      deploy-day checklist in deploy/README.md. Docker image builds.
- [x] 6c. README, docs/report.md (eval section placeholder EVAL_SUMMARY), docs/video-script.md.
- [x] 6d. Verification now checks photos against signed manifests; report seal links to move-in seal. 6 tests pass.
- [x] 7. Hill-climb: dark theme checked on the report, persona critique rounds 2 and 3, deslop pass on the diff.
- [ ] 8. Owner: run deploy/deploy.sh with AWS credentials, then follow "Before you submit" in deploy/README.md.
- [x] 9. Submission film: docs/video/twice-demo.mp4 (147 s, second pass after judge round 4, 1920x1080, 30 fps, -16 LUFS). Source: HyperFrames
      project video/twice-demo (SPEC.md, REVIEW.md). Kokoro voice, no music (needs HeyGen sign-in). Check passes;
      review sheets read and fixed. docs/video-script.md matches the film. Linked from the README.
      Owner: upload the MP4 to YouTube or Vimeo for Devpost. Raw footage (video/footage) is gitignored.
- [x] 10. docs/winners-research.md: 8 fetched winner write-ups, OpenCV winners 2021 to 2025 with sources, and a
      checklist against Twice. Open gaps it names: live endpoint (owner), no labelled real damage pairs, no real users.
- [x] 10b. Judge round 4 fixes (de0d9fb, 5ae1795, 17e1889): sample findings named from ground truth, zoomed
      move-in/move-out crops in the check and the report, ghost guide in the sample check, contrast token
      --on-signal, phone layout. Skipped: "Play all three spots" button.
- [x] 10c. Hybrid benchmark (server/eval/hybrid_bench.py, docs/evaluation.md 7.1): drawn defects on the 22 judged
      Oxford pairs. Recall 0.29, strict 0.18, precision 0.85, against 0.90 synthetic. README states 0.90 is an
      upper bound. Trees gives 0 of 71; tolerant vs plain difference is not settled.
- [ ] 11. Owner, optional: photograph 5 to 10 real move-in and move-out pairs with real marks, run them through the
      app, and add the results to docs/evaluation.md. Show the app to a few renters and note what they say.

## How to run locally
- API: `cd server && ../.venv/Scripts/python.exe -m uvicorn twice.app:app --reload --port 8000` (TWICE_DATA defaults to local store).
- Web: `cd web && npx vite --port 5288` (proxies /api to 8000). Port 5173 is used by another app.
- Tests: `cd server && ../.venv/Scripts/python.exe -m pytest -q tests` (10 pass).
- Bench: `cd server && python eval/bench.py` (about 15 min), then `python eval/agent_bench.py` (about 3 min, 5 seeds), `python eval/real_bench.py`.

## Surprises
- Vite can serve a module caught between two quick file writes; the browser then keeps that stale `?t=` URL. Touch the file to rebuild.
- The uvicorn `--reload` worker served old code for a while. The API now runs without `--reload`; restart it after server edits.
- On Windows, killing the uvicorn `--reload` parent left its worker holding port 8000 and serving stale code. Check `netstat -ano | grep :8000` after restarts.

- RANSAC (USAC MAGSAC) uses OpenCV's global RNG, so a result can depend on what ran earlier in the same process. Benchmarks seed it with cv2.setRNGSeed.

## Environment notes
- No AWS CLI or credentials on this machine. `envsync` is not installed at ~/.local/bin.
- Global CLAUDE.md default path `/Users/hridyaagrawal/honey` does not exist on this Windows machine; work stays in this repo.
- RTX 4070 Ti, Docker 27, Node 24, Python 3.14, uv available.
