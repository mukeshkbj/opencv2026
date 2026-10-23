# Twice

**Take the same photo twice. See what really changed. Sign the proof.**

Twice is renter-side evidence for apartments and rental cars. You photograph a few spots when you move in. When you move out, Twice puts a ghost of each first photo over your camera and guides you back to the same angle. OpenCV 5 aligns the two photos, finds what changed, and rules out shadows, lamps and reflections. When it is unsure, the agent asks for one more photo. The result is a signed report that anyone can verify.

Built for the OpenCV AI Competition 2026. OpenCV 5 does all the image analysis. The evidence store, signing key, captioning model and metrics run on AWS.

![Twice landing page](docs/img/landing.png)

## Why

Rental companies now scan returned cars with AI. One Hertz renter received a $440 bill for a one-inch scuff: $250 damage, $125 processing and $65 administration ([The Drive](https://www.thedrive.com/news/this-is-what-happens-when-hertzs-ai-scanner-finds-damage-on-your-rental)). A House subcommittee chair has asked Hertz to explain the system ([House Oversight](https://oversight.house.gov/release/mace-investigates-use-of-artificial-intelligence-for-car-rental-damage-assessments)). Landlords keep detailed move-out photos too. Most renters keep a few blurry phone shots that nobody can compare. Twice gives the renter the same quality of evidence as the company.

## What a judge can try in two minutes

1. Open the app and press **Try the sample check**. It loads three move-in photos that were sealed earlier: a living room, a desk and a rental car.
2. Press **Take the move-out photo** on each spot. The sample uses prepared photos instead of your camera.
3. Watch the agent. On the car, a reflection looks like damage. The agent asks for a side-step photo, sees the reflection move, and rules it out. The scratch stays.
4. Press **Create the signed report**. The report shows every finding, every ruled-out shadow, the SHA-256 of every photo and two signatures. The stamp turns green only when the server re-hashes every stored photo and both signatures check out.
5. Press **Download evidence bundle**, unzip it, and run `python verify.py`. It checks every photo and both signatures without the Twice server.

![The signed condition report](docs/img/report.png)

With a phone, press **Start my own** to run the same flow on your own room.

## How it works

![Architecture](docs/diagrams/architecture.png)

| Step | OpenCV 5 | What it does |
|---|---|---|
| Quality gate | `Laplacian`, `createCLAHE`, `SIFT` | The shutter waits until a move-in photo is sharp, lit and textured enough to match later. |
| Guide | `SIFT`, `findHomography` (`USAC_MAGSAC`) | Each live frame is matched to the move-in photo. The ghost overlay warps to the match, and the camera fires on its own after three aligned frames. |
| Register | `SIFT` + `FlannBasedMatcher`, `USAC_MAGSAC`, `warpPerspective`, `DISOpticalFlow` | The move-out photo is warped onto the move-in photo, then dense flow corrects the last few pixels. |
| Compare | `GaussianBlur`, local normalisation, `dilate`/`erode` envelopes, `connectedComponentsWithStats` | A shift-tolerant structure and colour difference, scored as a robust z-score. Blur, exposure and sub-pixel jitter do not count as change. |
| Decide | agent tools below | Every region gets a verdict: **Changed**, **Lighting only** or **Can't judge**. |
| Detect objects | `dnn.readNetFromONNX(..., engine=dnn.ENGINE_NEW)` with NanoDet-Plus | Labels a finding as "missing" or "new" when an object appears in only one photo. A person in the frame marks the finding as "can't judge". |

The agent is a rule planner with a budget of two follow-up photos per spot. Each tool result decides the next action, and the trace is shown in the app and stored in the report.

![Agent loop](docs/diagrams/agent-loop.png)

- `relight_check`: a smooth light field with no colour shift is a shadow or a lamp. Ruled out.
- `glare_check`: near-white pixels grew. The agent asks for a side-step photo. A reflection moves with the camera; damage stays on the surface.
- `size_check`: a small, weak change gets a close-up request. The close-up is compared at higher resolution.
- `object_check`: NanoDet on the new DNN engine, as above.
- `caption`: Claude on Amazon Bedrock names each confirmed change. It can label a finding or hand it to a human. It cannot delete a finding. Without Bedrock, rule-based labels are used.

### Evidence

Every photo is hashed with SHA-256 on arrival. The move-in set is sealed with a signed manifest before any move-out photo exists. The final report is a second signed manifest over all photos, findings and agent traces. On AWS the signer is an asymmetric KMS key (ECDSA P-256), and the photos sit in an S3 bucket with Object Lock. `GET /api/checks/{id}/verify` re-hashes every stored file and checks both signatures against the published public key. The report also offers an evidence bundle: a zip with the photos, the seals, the public key and `verify.py`. Anyone can run `python verify.py` on it without the Twice server.

## Evaluation

The full method, ablations, latency and a failure gallery are in [docs/evaluation.md](docs/evaluation.md).

Two benchmarks cover the engine.

- **Synthetic, full agent loop** (`server/eval/agent_bench.py`, 170 pairs with known damage, camera moves, exposure, colour, shadow and glare, plus the follow-up shots the agent asks for): recall 0.90, precision 0.99, 0.01 false "changed" findings per damage pair. Lighting-only pairs got a false alarm in 3% of cases. Every pair runs under 5 RANSAC seeds.
- **Real photos, nothing changed** (`server/eval/real_bench.py`, the Oxford affine sequences): of 40 pairs, 22 were judged. The agent asked for a retake on the other 18: 10 because the camera stood too far from the first spot, 8 because the photos could not be matched. Two judged pairs got a false alarm: trees and a harbour, where leaves and water may really move.

All three bundled samples resolve to their ground truth, including the reflection on the car. There is no set of real move-in and move-out pairs with labelled damage yet. That is the most important limit of this evaluation.

NanoDet-Plus runs in a median of 16.3 ms per frame on `ENGINE_NEW` against 56.5 ms on `ENGINE_CLASSIC` on the same CPU. Reproduce with `cd server && python -m eval.engines`.

## Run it locally

Requirements: Python 3.12 or newer, Node 24.

```bash
python -m venv .venv
.venv/bin/pip install -r server/requirements.txt        # Windows: .venv\Scripts\pip
cd server && ../.venv/bin/python -m uvicorn twice.app:app --port 8000
```

In a second shell:

```bash
cd web && npm ci && npx vite --port 5288
```

Open http://localhost:5288. Vite proxies `/api` to port 8000. Without AWS settings, photos go to `./data`, manifests are signed with a local Ed25519 key, and captions come from rules.

To run the production build in one container:

```bash
docker build -t twice .
docker run -p 8000:8000 twice
```

### Tests

```bash
cd server && ../.venv/bin/python -m pytest -q tests
python eval/synth.py <folder of photos> 40           # synthetic benchmark
python eval/bench.py                                  # engine level, see docs/evaluation.md
python eval/agent_bench.py                            # agent level, with follow-up photos
python eval/real_bench.py                             # real photos, false alarms only
```

The tests run the full sample flow through the API: seal, three move-out photos, follow-ups, signed report, verification, tamper tests that edit a stored photo or a signed record and expect verification to fail, and an offline check of the evidence bundle.

## Deploy to AWS

```bash
./deploy/deploy.sh
```

This builds an arm64 container for Lambda on Graviton behind a Function URL. The SAM template also creates the S3 evidence bucket (SSE-KMS, Object Lock, 30-day expiry), the KMS signing key, least-privilege IAM for Bedrock, a log group and an error alarm. Details and teardown steps: [deploy/README.md](deploy/README.md).

| Variable | Effect |
|---|---|
| `TWICE_BUCKET` | Store photos and manifests in this S3 bucket instead of `./data`. |
| `TWICE_KMS_KEY_ID` | Sign manifests with this KMS key (ECDSA_SHA_256) instead of a local Ed25519 key. |
| `TWICE_BEDROCK_REGION` | Caption confirmed findings with Claude on Bedrock in this region. |
| `TWICE_BEDROCK_MODEL` | Bedrock model ID. Default `anthropic.claude-opus-5-5`. |
| `TWICE_DATA` | Local storage folder when no bucket is set. |

## Responsible use

- Twice sorts differences into three answers and never hides one. "Can't judge" is a real answer, and the report asks a person to review every "Changed" and "Can't judge" item.
- The language model only names changes. Geometry and measured evidence decide every verdict.
- The report states what it cannot prove: it covers only the photographed spots, the times come from the server clock, and a valid signature does not prove a photo shows what it claims.
- Photos expire from the bucket after 30 days by default. The app has no accounts and collects no personal data beyond the photos.
- The sample damage is synthetic. The sample photos are credited below.

## Repository

```
server/twice/      FastAPI app, OpenCV engine (vision.py), agent, detector, evidence, storage
server/eval/       synthetic benchmark and full evaluation
server/samples/    sample check generator and hero export
server/tests/      API flow and detector tests
web/               React app (Vite): landing, guided capture, results, report
deploy/            SAM template and deploy script
docs/              spec, research, persona critique, evaluation, diagrams
```

## Credits

Sample photos via Wikimedia Commons: "Sunny Room in old Apartment" (CC BY 2.0), "Top Workspace Office" (CC0), "1970 AMC Hornet SST" (CC BY 4.0). NanoDet-Plus weights from [opencv_zoo](https://github.com/opencv/opencv_zoo) (Apache 2.0). Fonts: Gambetta and Switzer (Indian Type Foundry, ITF Free Font License), JetBrains Mono (OFL).
