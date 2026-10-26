# Devpost submission text

Paste each section into the matching Devpost field. Fill in the three links once they exist.

- **Repository:** https://github.com/mukeshkbj/twice (branch `twice`)
- **Live demo:** _Function URL from `sam deploy`_ (or offer a live screen-share demo)
- **Video:** _YouTube or Vimeo link (unlisted is fine)_

## Tagline

Take the same photo twice. See what really changed. Sign the proof.

## Inspiration

Rental companies now scan returned cars with AI. One Hertz renter got a $440 bill for a one-inch scuff ($250 damage, $125 processing, $65 admin), and a House subcommittee chair asked Hertz about damage assessments issued without human review. Landlords keep careful move-out photos too. Most renters have a few blurry phone shots that nobody can compare. We wanted the renter to have evidence as good as the company's.

## What it does

Twice is renter-side evidence for apartments and rental cars.

1. At move-in, you photograph a few spots. A quality gate waits until each photo is sharp and textured enough to match later. The set is hashed and sealed with a signature.
2. At move-out, Twice puts a ghost of each first photo over the camera and guides you back to the same angle.
3. OpenCV 5 aligns the two photos, finds what physically changed, and rules out shadows, lamps and exposure.
4. When a change could be a reflection, the agent asks for one more photo from a step to the side. A reflection moves with the camera; damage stays. If the camera did not really move, it asks again, and then hands the finding to a person.
5. The result is a signed report with every finding, every ruled-out shadow, the hash of every photo and the agent's full trace. Anyone can check it offline with the evidence bundle and `python verify.py`.

## How we built it

- **OpenCV 5:** SIFT and FLANN matching, a `USAC_MAGSAC` homography, `warpPerspective` and DIS optical flow for registration; a structure and colour z-score change map with `connectedComponentsWithStats`; NanoDet-Plus on the new DNN engine (`cv2.dnn.ENGINE_NEW`) to tell objects from surface marks.
- **Agent:** a perception-decision-action loop with tools `relight_check`, `glare_check`, `parallax_check`, `size_check` and `object_check`, and a budget of two follow-up photos per spot. Every decision is logged with the measurement that caused it and signed into the report.
- **MCP:** the same OpenCV 5 tools are exposed as an MCP server, so any agent (Claude Desktop, Claude Code, or our own runner) can run a check through them.
- **AWS:** one container on Lambda (arm64, Graviton) behind a Function URL; S3 with Object Lock and SSE-KMS for evidence; an asymmetric KMS key (ECDSA P-256) for signatures; Claude on Bedrock for plain-language labels (it can name a change or flag it for a human, never change a verdict); CloudWatch metrics for latency and every agent decision. A COOL kit runs the same check on Graviton4 against pip OpenCV on Arm and x86.
- **Web:** React and Vite, phone and desktop layouts.

## Evaluation

- **Agent level** (170 synthetic pairs × 5 RANSAC seeds = 850 runs, follow-up photos included): defect recall 0.88, precision 1.00; 754 of 850 runs fully correct. The agent asked for a side-step photo in 70 of 75 reflection runs, and all 70 ended correctly.
- **Real photos of unchanged scenes** (Oxford affine sequences): 0 false alarms on 22 judged pairs; views too far away get a retake request instead.
- **Hybrid** (drawn defects on real photos): recall 0.24, precision 0.96. The synthetic numbers are an upper bound, and we say so.
- Failure gallery, ablations and methods are in `docs/evaluation.md`.

## Challenges we ran into

- Reflections look exactly like scratches in a single comparison. The side-step photo and the check that the camera really moved were the fix.
- RANSAC uses OpenCV's global RNG, so a result could depend on what ran earlier. Every benchmark now seeds it and reports five seeds.
- Getting real damage pairs is hard. We built three benchmarks and report the weakest number alongside the best one.

## Accomplishments that we're proud of

- A counterfactual trace where only the photo differs and the agent's next action changes.
- Evidence that can be checked without trusting our server.
- A sample check a judge can finish in two minutes.

## What we learned

Most of the work in change detection is ruling things out: light, exposure, small shifts, reflections. Saying "can't judge" honestly is better than a confident wrong answer.

## What's next

Real move-in and move-out pairs with real marks, a study with renters, and a COOL run on Graviton4 to measure the speed-up.

## Responsible use

Twice gives evidence, not verdicts. The report asks a person to review every "Changed" and "Can't judge" item. The language model cannot add, delete or change a verdict. Photos expire after 30 days, are encrypted with KMS, and are only stored for the check that made them.

## Built with

opencv, python, fastapi, numpy, react, typescript, vite, aws-lambda, amazon-s3, aws-kms, amazon-bedrock, amazon-cloudwatch, aws-sam, docker, graviton, mcp, claude

## Special awards to tick

- **Agentic Vision Award:** yes. Evidence: `docs/agentic-vision.md`.
- **Best Use of COOL:** only if `python deploy/cool/cool.py bench` produced results in `docs/eval/cool/`.
