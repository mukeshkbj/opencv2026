# Twice: technical report

OpenCV AI Competition 2026. Repository: this repo. Live endpoint: see README.

## 1. Problem

Rental companies and landlords document the condition of a car or an apartment with detailed photos and, increasingly, with AI scanners. Renters rarely have comparable evidence. A Hertz renter received a $440 bill for a one-inch wheel scuff found by an airport scanner, minutes after the return ([The Drive](https://www.thedrive.com/news/this-is-what-happens-when-hertzs-ai-scanner-finds-damage-on-your-rental)). A House subcommittee chair wrote that Hertz is the only rental company that issues these damage assessments without human review, and asked Hertz for a briefing ([House Oversight](https://oversight.house.gov/release/mace-investigates-use-of-artificial-intelligence-for-car-rental-damage-assessments), [Repairer Driven News](https://www.repairerdrivennews.com/2025/08/25/subcommittee-requests-briefing-from-hertz-on-ai-scanning-technology/)). In apartments, deposit disputes follow the same pattern: the landlord has move-out photos, and the tenant has a few unmatched phone shots.

Unmatched photos fail as evidence for three reasons:

1. They are taken from different angles, so nobody can say whether a mark is new.
2. Light changes between visits. Shadows, lamps and reflections look like damage in a naive comparison.
3. Nothing proves the photos were not edited or swapped later.

Twice addresses all three. It guides the second photo to the angle of the first, separates real change from lighting, and signs the photos and findings.

## 2. Users and flow

- **Renter** (primary user). Shoots three to six spots at move-in. The shutter enables only when a photo is sharp, lit and textured enough to match later. The set is sealed with a signature before any move-out photo exists.
- **Renter at move-out.** A ghost of each move-in photo floats over the camera. Live frames are matched to the reference, and the app tells the user how to move ("Pan left", "Move closer"). It shoots on its own when the view locks.
- **Counterparty** (landlord, fleet manager, small-claims reviewer). Receives a link to the report. The report shows aligned pairs, numbered findings with measured evidence, the SHA-256 of every photo, two signatures, and a list of what the report cannot prove. A verify endpoint re-hashes every stored photo.

## 3. System

![Architecture](diagrams/architecture.png)

One container serves the React app and the FastAPI backend. On AWS it runs on Lambda (arm64, Graviton) behind a Function URL, with the Lambda Web Adapter. The same image runs locally with `docker run`.

| Concern | Local | AWS |
|---|---|---|
| Photo and manifest storage | `./data` | S3, SSE-KMS, versioning, Object Lock (governance, 1 day), 30-day expiry |
| Manifest signing | Ed25519 key on disk | KMS asymmetric key, ECDSA P-256, `Sign` with a SHA-256 digest |
| Finding labels | Rule-based labels | Claude on Amazon Bedrock, JSON-schema output |
| Metrics | JSON log lines | CloudWatch Embedded Metric Format, error alarm |

The browser shrinks every photo to at most 2400 px before upload, which keeps requests under the 6 MB Function URL limit.

## 4. Computer vision

All image analysis uses OpenCV 5.0.0 (`opencv-contrib-python-headless`). The engine is `server/twice/vision.py`.

**What is specific to OpenCV 5.** Most calls here (SIFT, USAC MAGSAC, DIS optical flow, CLAHE) also exist in OpenCV 4. The part that needs OpenCV 5 is the new DNN engine: the object check loads NanoDet-Plus with `engine=cv2.dnn.ENGINE_NEW` and runs it 3.2 to 3.5 times faster than the classic engine on the same CPU (section 4.6). The rest of the pipeline is ordinary, well-tested OpenCV, combined in a new way: guided re-capture, a lighting-aware change map and an agent that decides which photo to take next.

### 4.1 Capture quality gate

Each preview frame is scored for brightness, clipped highlights, sharpness (variance of the Laplacian) and the number of SIFT features on a CLAHE-equalised image. A photo with fewer than 80 features or a sharpness below 60 is rejected, because it cannot be registered reliably months later.

### 4.2 Guided re-capture

The move-in photo is stored with SIFT keypoints at two resolutions: 1024 px for analysis and 480 px for live guidance. Each live frame is matched with a FLANN matcher and Lowe's ratio test (0.75). A homography is fitted with `cv2.USAC_MAGSAC` (threshold 3 px, at least 25 inliers) and checked for plausibility (area ratio, convexity, corner spread). The homography is decomposed into a shift, a scale and a roll, which drive the on-screen instruction. The ghost overlay is warped in CSS with a `matrix3d` built from the projected corners. The app captures automatically after three consecutive aligned frames with an alignment score above 0.72.

### 4.3 Registration

The move-out photo is matched to the move-in photo the same way, then warped with `warpPerspective`. Pixels outside the warped area are filled from the move-in photo so they cannot produce change. Dense `DISOpticalFlow` (medium preset) on the aligned pair corrects residual parallax and lens differences. The flow is clamped so it cannot "explain away" a real change by moving pixels far.

### 4.4 Change map

A naive absolute difference of the photos flags every exposure change, every shadow and every edge after a sub-pixel shift. The change map is built in four steps:

1. Both images are converted to Lab and blurred with a Gaussian (σ = 1).
2. The L channel is locally normalised: subtract a local mean and divide by a local standard deviation (σ = 12). This removes exposure and gain changes.
3. **Difference.** The first comparison takes the plain absolute difference of the two normalised images, after the flow refinement of section 4.3. The side-step and close-up photos move the camera on purpose, so they use a shift-tolerant difference. It compares each pixel with the other image's min/max envelope over a 1 px window (`dilate` / `erode`), in both directions. A value inside the envelope counts as zero. This removes edge ghosts from misalignment but keeps new texture.
4. **Robust z-score.** The difference is standardised by its noise level. The median absolute deviation collapses to zero for a tolerant difference, so the scale falls back to the 95th-percentile tail.

A pixel is a candidate when its z-score exceeds 9 and an absolute gate also passes (L difference above 9 after gain compensation, or a chroma difference above 6). Clipped highlights and a thin border band are masked. Speckle is removed with a morphological opening, nearby fragments are grouped by dilation, and overlapping boxes are merged so one physical mark is one finding.

### 4.5 Lighting and reflections

For every region, two measurements separate light from damage:

- **Illumination likeness.** A smooth multiplicative light field is fitted to the log ratio of the two images. If it explains more than 80 % of the change and the chroma shift is small, the region is lighting only. Large smooth regions (shadows, lamps, sun patches) are also reported as separate "lighting only" findings, so the report can show what was ignored.
- **Brightening.** The share of pixels that newly reach near-white (above 250 after gain compensation, or above 253 in the move-out photo whatever the gain). A reflection appearing or vanishing changes this share. It cannot be resolved from one photo, so it triggers a parallax request (section 5).

### 4.6 Objects on the new DNN engine

NanoDet-Plus (416 × 416, from opencv_zoo) runs on both aligned photos with `cv2.dnn.readNetFromONNX(path, engine=cv2.dnn.ENGINE_NEW)`. On the development CPU, the new engine runs the model in a median of 16.3 ms per frame against 56.5 ms on `ENGINE_CLASSIC` (100 runs after 10 warm-up runs, 32 threads on an i9-13900K, `python -m eval.engines`). A later rerun gave 17.7 ms against 56.4 ms, with 90th percentiles of 19.0 ms and 59.4 ms. That is 3.2 to 3.5 times faster. The two engines return the six output tensors in different orders, so the decoder pairs them by shape instead of by index.

## 5. Agent

![Agent loop](diagrams/agent-loop.png)

The agent (`server/twice/agent.py`) is a rule planner. Its tools are OpenCV measurements, and every decision is logged with the measurement that caused it. The trace is shown in the app and stored in the signed report. Each spot has a budget of two follow-up photos.

| Tool | Trigger | Next action |
|---|---|---|
| `register` | every move-out photo | Fewer than 25 inliers, an implausible homography, or a view too far from the first one (scale outside 0.8 to 1.25, strong tilt): ask for a retake. |
| `relight_check` | smooth light field explains the change, low chroma | Rule out as lighting. |
| `glare_check` | near-white share changed by more than 5 % | Request a side-step (parallax) photo. If the change vanishes, it was a reflection. If it persists at the same surface position, it is damage. |
| `parallax_check` | a side-step photo arrives | The homography shows how far the camera moved. Under 1% of the frame, the photo is not evidence: ask again, then mark "can't judge". |
| `relight_check` (soft) | shadow-like edges but a colour shift | Request a close-up. |
| `size_check` | small region (under 0.15 % of the view) with a weak peak | Request a close-up. The close-up is cropped around the box, upscaled up to 2x and compared again. |
| `object_check` | any finding not ruled out | A person over the finding in only the move-out photo: "can't judge". An object present in only one photo: label it "missing" or "new". |
| `budget` | no follow-ups left | Mark unresolved findings "can't judge". |
| `caption` | confirmed changes | Claude on Bedrock names the change, or flags it for a human. Without Bedrock, rule labels. |

This satisfies the Agentic Vision criterion directly: a vision measurement (the brightening share, the region size, the soft-edge test) decides whether the agent asks for another photo, and which kind.

The language model is deliberately weak. It receives the crops of a finding and returns a short label and a `needs_human` flag. If it cannot name the change, the finding gets a note for a human reviewer. It cannot add, delete or change a finding's verdict. If Bedrock fails, the rule label is used. Geometry and measurement own every verdict.

## 6. Evidence and verification

- Every uploaded photo is hashed with SHA-256 on arrival and stored under its spot.
- **Seal 1** (move-in): a canonical JSON manifest (sorted keys, no whitespace) lists every move-in photo hash and time. It is signed before any move-out photo can be added; the API returns 409 for new spots after sealing.
- **Seal 2** (report): a manifest over all photos, follow-ups, findings, evidence and agent traces, plus the digest of seal 1.
- `GET /api/checks/{id}/verify` re-reads every stored photo, recomputes its hash, recomputes both manifest digests and checks both signatures with the public key. The test suite edits a stored photo and expects verification to fail.
- **Offline check.** `GET /api/checks/{id}/bundle` returns a zip with every photo (named by its hash), both seals, the public key and `verify.py` (`server/twice/offline_verify.py`). It needs only Python and `cryptography`, so a landlord, a rental company or a court can check the report without trusting the Twice server. It prints the key fingerprint, which the report page also shows. A test edits a photo and a finding inside a bundle and expects both to fail.

## 7. Evaluation

Summary here; full tables, ablations, latency and the failure gallery are in [evaluation.md](evaluation.md).

Four benchmarks measure four levels. All numbers come from scripts in `server/eval/` with fixed seeds.

| Benchmark | Data | Result |
| --- | --- | --- |
| Agent level (`agent_bench.py`) | 170 synthetic pairs: 80 with 162 drawn defects, 30 with no change, 60 with only an exposure, colour, shadow or glare change. The agent's follow-up photos are generated too | Recall 0.878 (142 or 143 of 162 defects), precision 1.000, under each of 5 RANSAC seeds. A false "changed" in 1 of 30 no-change pairs and in 1 or 2 of 60 lighting-only pairs. 0.20 follow-up photos per pair |
| Engine level (`bench.py`) | The same 170 pairs through `compare` alone, plus 288 registration stress pairs | Recall 0.907, precision 0.993, strict recall (IoU of at least 0.3) 0.704. Every glare pair is flagged at this level and resolved by the agent |
| Real photos (`real_bench.py`) | 40 pairs from the Oxford affine sequences, where nothing changes | 22 pairs judged, 18 sent back for a retake. No judged pair got a false "changed" |
| Hybrid (`hybrid_bench.py`) | The 22 judged Oxford pairs with synthetic defects drawn onto the move-out photo: 176 damage runs, 370 defects | Recall 0.241, strict recall 0.159, precision 0.957, against 0.878 recall on the synthetic pairs. With the tolerant difference in the first pass: 0.289, 0.178 and 0.849. Drawn defects are not real damage |

Registration stays accurate to 150 degrees of rotation, a 2.2 times zoom and 30 degrees of tilt. The agent asks for a retake when the local scale at the centre or a corner differs by more than 1.25 times, or the view is strongly tilted, because a photo from another distance shows the surface at another resolution. This rule cut the real-photo false alarms from 7 pairs to 2. The plain first-pass difference then removed the last 2. A full compare takes a median of 1.50 s on a desktop CPU.

The evaluation drove seven engine changes: an exposure-matched border fill, a sharp-edge test that stops the lighting test from hiding scratches in shadows, a chroma noise floor, a glare veil test, the retake rule, the plain difference in the first pass and a glare test that counts clipped pixels as near-white. The first five raised agent-level recall from 0.852 to 0.901 and precision from 0.972 to 0.993. The last two traded recall for precision: agent-level recall is now 0.878 and precision 1.000. Lighting-only false alarms fell from 30% to 2.3% of pairs.

The ablations show that local normalisation is essential (recall 0.247 without it). On synthetic data, the plain and the shift-tolerant difference have nearly the same recall (0.907 and 0.914), and the tolerant one has far more false positives (0.14 per pair against 0.01). The first comparison therefore uses the plain difference. The agent, real and hybrid benchmarks all showed fewer false alarms with it, for a loss in recall. The side-step and close-up photos keep a 1 px tolerance, because they move the camera on purpose, and the plain difference there broke the parallax check on the sample car. The failure gallery shows faint stains and chips (contrast below 15 grey levels), a crack inside a colour-shifted region, small flags on a white bag in a colour-cast pair, and flags left over from glare.

The main limit: there is no set of real move-in and move-out photos with labelled damage. The real-photo benchmark measures false alarms only, and the hybrid benchmark uses drawn defects. The choice of the plain difference came after the real and hybrid results, so those sets are no longer fully untouched.

## 8. Responsible operation

- **Three answers, never hidden.** Every difference ends as Changed, Lighting only or Can't judge, and all three appear in the report.
- **A human reviews.** The report says that findings are measurements, not legal conclusions.
- **Limits are printed.** The report states that it covers only the photographed spots, that times come from the server clock, and that a valid signature does not prove a photo shows what it claims.
- **Data minimisation.** No accounts. Photos expire after 30 days by default. The bucket blocks public access and denies non-TLS requests.
- **Least privilege.** The Lambda role can only read and write its bucket, sign with its key, and invoke the configured Claude model.
- **Cost.** One analysis is one Lambda invocation at 3 GB. Its time on Lambda is not measured yet; on one desktop CPU thread a compare takes a median of 3.2 s, plus one short Bedrock call per confirmed change. Reserved concurrency of 10 caps the spend under abuse. The camera waits for each guide answer before it sends the next frame, so one user holds at most one execution at a time and the cap serves about ten users at once. Raise it in `template.yaml` for a larger audience. If an alarm address is set, an AWS Budget emails at 80 % of 25 USD a month.

## 9. Limitations

- The damage evaluation uses real photos with synthetic damage. The real-photo benchmark has no damage, so it measures false alarms only. There is no set of real move-in and move-out pairs with labelled damage yet.
- Strong parallax (a door that moved, a chair pushed aside) is reported as change. That is correct for the renter but can look noisy.
- Very low texture surfaces (a freshly painted white wall) can fail the quality gate or registration. The app asks for an edge or a corner in the frame.
- Server timestamps prove when the server received a photo, not when it was taken. A trusted-time service or a counterparty acknowledgment at move-in would close that gap.
- NanoDet knows the 80 COCO classes. Most damage is not an object, so `object_check` mostly labels missing furniture and items, and catches people in frame.

## 10. Future work

- A counterparty acknowledgment: the landlord or agent co-signs the move-in seal on the spot.
- A real-photo benchmark collected with volunteers across apartments and cars.
- On-device guidance with opencv.js 5 to remove the network round trip from the ghost overlay.
