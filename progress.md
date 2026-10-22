# Progress

Target: OpenCV AI Competition 2026 (Devpost). Deadline: 2026-10-26 23:59 PT.

## Hard requirements (from the rules page)
- OpenCV 5 does substantive image or video analysis.
- A meaningful component runs on AWS.
- Technical report, judge-accessible repo, pinned dependencies, build/deploy/test instructions.
- Architecture diagram (OpenCV 5 + AWS + agent components).
- Working web endpoint or live demo. Video of 5 minutes or less.
- Evaluation evidence, including failure cases.

Rubric: technical 30, innovation 20, impact 20, UX 10, docs 10, cloud/responsible ops 10.
Special awards: Agentic Vision (vision output must change the next agent action), Best Use of COOL.
Judges named: Gary Bradski (OpenCV founder), Phil Nelson.

## Phases
- [ ] 1. Research (past winners, OpenCV 5 features, design references) — agents running
- [ ] 2. Idea candidates + persona critique
- [ ] 3. Architecture + CV pipeline prototype
- [ ] 4. Web app (award-level UI)
- [ ] 5. AWS deploy kit (no AWS credentials on this machine; the user deploys)
- [ ] 6. Evaluation, report, diagram, video script
- [ ] 7. Hill-climb passes (UI, perf, features)

## Environment notes
- No AWS CLI or credentials on this machine. `envsync` is not installed at ~/.local/bin.
- Global CLAUDE.md default path `/Users/hridyaagrawal/honey` does not exist on this Windows machine; work stays in this repo.
- RTX 4070 Ti, Docker 27, Node 24, Python 3.14, uv, fly CLI available.
