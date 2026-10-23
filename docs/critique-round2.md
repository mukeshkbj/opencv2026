# Persona critique, round 2

> **Status, 2026-10-23:** the findings below were applied. Item 6e in `progress.md` lists the fixes. The text below is the original critique.

This round reviews the built product, not the plan. The reviewer read the README, the spec, the engine, the agent, the API, the SAM template and the web app. The reviewer also ran the app, took screenshots at 1440 and 500 pixels wide, and attacked the API.

Evidence gathered:

- Screenshots of the landing page, the check page and the report, in light mode, with reduced motion on and off.
- A scripted run of the sample flow, followed by an attempt to change the report after signing.
- A timing run of the engine on the three sample pairs.
- A fetch of the Straight Arrow News article that the README cites.
- The test suite: five tests pass.
- The screenshot tool renders a minimum of 500 pixels wide, so the 390 pixel crops cut at the right edge are a tool artefact. The 500 pixel render shows no overflow.

## Blocking findings

Three findings can lose the competition by themselves. They come first because every persona is affected.

1. **A signed report can be changed after signing, and verification still says OK.** The reviewer ran the sample flow, signed the report, then posted the move-in photo as the new move-out photo of spot 1. The API accepted it. `GET /verify` returned `ok: true`. The signed manifest still holds the old photo hash, while the check now holds a new one. `verify()` in `server/twice/app.py` checks that each file matches the hash in `check.json`, and that each seal is self-consistent. It never compares the signed manifest with the current state. `run_after` and `run_followup` also never check whether a report seal exists. The green VERIFIED stamp is therefore not evidence of the claim "any edit breaks the signature".
2. **No live AWS endpoint exists.** The competition requires a web endpoint and a meaningful AWS component. `progress.md` states that this machine has no AWS credentials. The README has no URL. The report says "Live endpoint: see README", and the README has none. The local `/api/health` reports `Ed25519` and `rules`, not KMS and Bedrock. The template, the KMS signing path and the Bedrock caption path have never run. Several details are unverified: the S3 write uses `aws:kms` without a key id, and the Bedrock Mantle IAM actions are unchecked. A failed caption call demotes every confirmed finding to "Can't judge".
3. **The evaluation evidence is missing.** The README links to `docs/evaluation.md`, which does not exist. The `docs/eval` folder holds an empty `failures` folder and no `results.json`. The report contains the literal placeholder `EVAL_SUMMARY`. The rules require failure cases. The headline numbers (0.91, 0.84, 0.35) come from synthetic pairs, and no committed output reproduces them.

## Persona 1: Gary Bradski, OpenCV founder

Question he asks: does this use OpenCV 5 in a way that matters, and do the numbers deserve belief?

| Criterion | Score | Reason |
|---|---|---|
| Technical (30) | 5 | The change map is thoughtful. The evidence is synthetic and tuned in sample. |
| Innovation (20) | 6 | The shift-tolerant envelope difference and the parallax test are a good idea. |
| Impact (20) | 6 | The problem is real. The method is unproven on real photos. |
| UX (10) | 7 | The ghost overlay is the best visual in the entry. |
| Docs (10) | 4 | Missing evaluation file, placeholder text, dead links. |
| Cloud and ops (10) | 4 | Nothing is deployed. |

What he sees:

- Almost every call is OpenCV 4.x: `SIFT`, `FlannBasedMatcher`, `findHomography` with `USAC_MAGSAC`, `DISOpticalFlow`, `connectedComponentsWithStats`. The only OpenCV 5 specific item is `readNetFromONNX(..., engine=ENGINE_NEW)`. The README never says which parts are new in 5.0. He will ask why this needs version 5.
- The speed claim, 10.8 ms against 55.5 ms, has no script in the repository. `docs/research.md` records an earlier "17 to 20 ms against 57 ms, indicative". One machine, no repeat count, no variance.
- The benchmark builds the "after" image from the same photo by a homography. There is no parallax, no lens or sensor difference, no auto exposure and no rolling shutter. That is the easy case. The README admits that no real pairs exist, and it is right to.
- A hit counts when any ground-truth pixel falls inside a detected box. That is lenient. `bench.py` also computes an IoU 0.3 recall, but the README quotes only the lenient one.
- The threshold `z_thresh=9` and the lighting cut 0.8 were most likely tuned on the same synthetic generator that reports the score. There is no held-out split.
- The lighting rule has a built-in blind spot. A soft dark smudge or a water mark with little colour shift looks like a smooth light field, so it is ruled out as lighting. The benchmark never tests that class, so the 0.91 hides it.
- On non-planar scenes a single homography plus clamped flow leaves parallax residue. The report admits that moved furniture is reported as change. The first-round objection about planes is only half answered.

Three changes that would most raise his score:

1. **Add a real-pair test set.** Shoot 20 to 30 pairs on two phones, with real exposure drift, a real step to the side, and a few planted marks (a sticky dot, a pencil line, a coffee ring). Report recall and false alarms with counts and intervals. Commit the pairs and a script, `server/eval/real.py`. Even a small honest set beats a large synthetic one.
2. **Split the benchmark.** Tune thresholds on one set of scenes and report on a different set. Add a "dark soft stain on a plain wall" class and a "shadow with a hard edge" class to `server/eval/synth.py`. Quote IoU recall next to the lenient number.
3. **Make the OpenCV 5 case concrete.** Add `server/eval/dnn_engine.py`, which times `ENGINE_NEW` and `ENGINE_CLASSIC` with 100 runs and prints median and spread. Add a short table in the report, "What is new in 5.0 and where we use it". Say plainly that the rest is stable 4.x API running on 5.0.

## Persona 2: Phil Nelson, OpenCV content and demos

Question he asks: would a normal person get this in ten seconds, and can I film it?

| Criterion | Score | Reason |
|---|---|---|
| Technical (30) | 6 | Good depth behind a clear story. |
| Innovation (20) | 7 | "Take it twice" is memorable. The ghost lock is a hook. |
| Impact (20) | 7 | The $440 bill gives it stakes. |
| UX (10) | 8 | The landing page is calm and clear. |
| Docs (10) | 5 | The README is strong. Linked files are missing. |
| Cloud and ops (10) | 4 | Cannot demo the cloud. |

What he sees:

- The hero loop is strong. The headline "Take it twice." and the ghost overlay explain the product without words.
- The hero labels are fixed copy: "Wall stain, new", "Floor scuff, new", "Coffee ring, new", "Item missing". The product with its rule captioner says "New mark or scratch on the surface" and "Object added, moved, or removed". The desk finding for the coffee ring reads "Darker mark or scratch on the surface" with the evidence "turned near white: possible reflection". A judge who runs the sample after the hero will see the gap.
- Three of the five findings on the sample report carry vague, scratch-like labels. Without Bedrock the app looks less smart than the landing page promises.
- The agent moment is the best part of the product, and it sits on screen two of the check page, below the fold. The video script depends on it.
- The "Start my own" path needs a phone camera and HTTPS. On a laptop it is a dead end. No fallback to file upload is mentioned in the UI.
- The video script runs 4:30 and covers the flow. It promises a `curl` showing the KMS signer and the Bedrock captioner. Today that output cannot be produced.

Three changes that would most raise his score:

1. **Make the demo path show the agent in the first screen.** In `CheckPage.tsx`, scroll the "The agent needs one more photo" card into view and pulse it once after each sample shot. Order the sample so the car spot comes first.
2. **Make the labels match the hero.** Give each sample spot a `truth` label in `sample.json`, and have the rule captioner use it for samples, or run Bedrock for the recorded demo. At minimum, rewrite the hero tags to match what the app says.
3. **Add a no-camera path for "Start my own".** Let the user pick two files from disk. Reviewers on a laptop can then try their own photos. Add a one-line note on the landing page that the camera needs a phone.

## Persona 3: AWS solutions architect

Question she asks: is AWS meaningful or bolted on, and is it safe and cheap to run?

| Criterion | Score | Reason |
|---|---|---|
| Technical (30) | 5 | Sound shape, never run. |
| Innovation (20) | 6 | KMS signing of evidence is a real fit. |
| Impact (20) | 6 | Fine. |
| UX (10) | 6 | Not her focus. |
| Docs (10) | 6 | `deploy/README.md` is good. |
| Cloud and ops (10) | 4 | Good template, no deployment, no abuse controls. |

What she sees:

- The choices are sensible: Lambda on Graviton, S3 with SSE-KMS and Object Lock, a KMS asymmetric signing key, Bedrock, EMF metrics and one alarm. The use of KMS for signature is meaningful, not decoration.
- None of it has run. The first deploy is likely to hit at least one of these: the key id missing on the S3 put, the Bedrock Mantle permissions, the 60 second timeout on a cold container that loads OpenCV, `anthropic`, `boto3` and an ONNX model.
- The Function URL has `AuthType: NONE`, CORS `*`, no WAF, no throttle and no reserved concurrency. Anyone can create checks, call the guide route in a loop, and trigger Bedrock calls and KMS signs. The round 1 response promised a "Bedrock budget" and per-session caps. Only the 4 MB size cap and the two-follow-up cap exist.
- The live guide route sends one request per frame, about every 200 to 800 ms. Each request reads `check.json` from S3 and may rebuild SIFT features on a cold container. That is the most expensive and the most latency-sensitive path, and it is not measured on Lambda.
- A check id is the only secret. There is no list endpoint, which is good. There is also no owner, so any holder of the share link can post photos, as the attack above shows.
- Object Lock is on the bucket, but `check.json` is rewritten in place. The lock protects old versions, yet the app never reads or publishes them.
- The report says "about one second at 3 GB". That is a local figure. The local timing was 0.33 to 0.42 s for the compare call alone on a fast desktop CPU, and the app logged 1.1 s under load.

Three changes that would most raise her score:

1. **Deploy once and capture the proof.** Run `deploy/deploy.sh`, keep the stack up through judging, and put the Function URL in the README. Save the `/api/health` output (KMS, Bedrock), one CloudWatch metrics screenshot and one X-Ray or log excerpt in `docs/`. Fix whatever breaks on first run, starting with the KMS key id on S3 puts.
2. **Add cheap abuse limits to the template.** Set `ReservedConcurrentExecutions` to a small number, add an AWS Budgets alarm, add a per-check cap on follow-ups and report calls in `app.py`, and put CloudFront with a WAF rate rule in front, or at least document why not. Cache `before_frames` state per check in `/tmp`.
3. **Use S3 versions as evidence.** Write each photo to a content-addressed key (`sha256/<hash>.jpg`) and refuse to overwrite. Then Object Lock actually protects what the manifest signs, and the "photos sit in a bucket with Object Lock" claim carries weight.

## Persona 4: a renter holding a $440 damage bill

Question they ask: would I use this, and what would confuse me?

| Criterion | Score | Reason |
|---|---|---|
| Technical (30) | 6 | They cannot judge it. They trust the demo. |
| Innovation (20) | 7 | The idea clicks. |
| Impact (20) | 8 | Exactly their problem. |
| UX (10) | 6 | Good flow, some jargon, and a timing gap. |
| Docs (10) | 5 | They never read the README. |
| Cloud and ops (10) | 5 | They worry about where the photos go. |

What they see:

- The pitch is clear. The $440 receipt on the landing page lands.
- The tool helps only if they took photos at move-in. A renter with a bill today cannot use it. The landing page never says what to do if the move-in photos do not exist.
- Moving in is busy. The promise "a minute per spot" is believable, but the app has no reminder, no saved link on the phone and no way to come back months later except a URL. A lost URL means lost evidence. There is no account and no email option.
- Words that confuse: "sealed", "Ed25519", "digest", "signature valid", "inliers", "z=26.1", "peak z=95.8". The check page shows these to a person who only wants to know whether the stain counts.
- The report says "Can't judge" is a real answer. That is fair, but the page does not tell a renter what to do next with a "Can't judge".
- The disclaimer "Times come from the server clock" is honest, but it weakens the product at the exact moment the renter needs trust. They will ask whether the company will accept it.
- A renter who sees "Changed" on a scuff that was already there will worry. Nothing explains how to dispute a finding or add a note.

Three changes that would most raise their score:

1. **Add a "keep my check" step at seal time.** On sealing, show the link, offer a copy button, a QR code and an optional email to self (`mailto:` link is enough). Put the line "Save this link. It is the only copy of your key" next to the seal.
2. **Hide the maths behind a toggle.** In `CheckPage.tsx` and `ReportPage.tsx`, show plain sentences first ("This area is darker and has a new edge"), and put z-scores and hashes under "Show the measurements". Replace "Ed25519" and "digest" with "digital signature".
3. **Let the renter add a note per finding, and say what to do.** Add a text field per finding ("This was there at move-in, see photo 3") and a one-line next step under "Can't judge": "Take one more photo, or ask the other party to look."

## Persona 5: a fleet or property manager, the counterparty

Question they ask: would I accept this as evidence, and how easily can I dismiss it?

| Criterion | Score | Reason |
|---|---|---|
| Technical (30) | 4 | Self-signed by a service they did not choose. |
| Innovation (20) | 5 | Fine. |
| Impact (20) | 6 | Useful if the other side already trusts it. |
| UX (10) | 7 | The report reads well and prints. |
| Docs (10) | 5 | Limits are honest. |
| Cloud and ops (10) | 5 | A hosted service they cannot audit. |

What they see:

- The report reads like an exhibit pack, with numbered marks and a limits box. That is persuasive.
- The easiest dismissals, in order:
  1. "The photographer chose the angles and the spots." The report says so itself.
  2. "The timestamps are the server's, not the camera's." The report says so too. There is no EXIF check, no capture time from the phone and no trusted time source.
  3. "Anyone with the link can change the photos." The attack above shows this is true, and verify does not catch it.
  4. "The service signed what it was given." The renter can reseal by calling the report endpoint again. The counterparty never saw the move-in set.
- The share link in the spec ("the other party can see the set") exists only as a report link. The counterparty cannot acknowledge the move-in seal. The report lists this as future work, and it is the feature that would make them accept it.
- Verification runs on the same server that holds the data. A manager cannot re-check offline. "Download evidence file" gives JSON, but no verifier script or documented steps.
- The README says the report seals "findings and agent traces". The code seals only id, box, verdict, kind and caption. The evidence text and the trace are not in the signed manifest. The report document says seal 2 includes "the digest of seal 1". The code does not.

Three changes that would most raise their score:

1. **Fix the post-signing hole and bind the seals.** In `verify()`, rebuild the manifest from current state and compare it with each seal. Reject `after`, `followup` and `spot` writes once a report seal exists, or version the check. Put the digest of seal 1 inside seal 2. Add a failing test to `server/tests/test_flow.py` for the exact attack above.
2. **Add a counterparty acknowledgment.** Give the move-in link a "I have seen this set" button that records a second signature or a timestamped hash from the other party. Even a single click that stores the receipt in the manifest changes the standing of the evidence.
3. **Ship an offline verifier.** Add `tools/verify.py` (about 40 lines using `cryptography`) that takes the evidence JSON and the public key, recomputes the hashes of the included photos and checks both signatures. Link it from the report page. Include EXIF capture time in the manifest, flagged "unverified".

## Persona 6: an Awwwards juror

Question they ask: is the craft at site-of-the-year level on desktop and mobile?

| Criterion | Score | Reason |
|---|---|---|
| Design | 7.5 | Confident type and palette, a strong hero. |
| Usability | 7 | Clear flow, some dense areas. |
| Creativity | 7.5 | The ghost lock is a real idea. |
| Content | 6.5 | Fixed hero labels, jargon in the app. |

What works:

- The Gambetta serif headline with the orange italic "twice." gives a clear voice. Switzer for text and JetBrains Mono for data is a good, restrained pairing.
- The warm paper background, the orange accent and the hairline rules feel designed, not templated.
- The reduced-motion end state of the hero (shadow tag, two marks, dashed box) reads cleanly in one frame.
- The report is the best page: the green stamp, the exhibit pairs, the numbered marks, the print styles.

Defects seen in the screenshots:

- **Hero, desktop, animated state.** The ghost frame shows a heavy double image with a visible wedge at the top edge (the warped photo does not fill the frame). The frame corner marks sit on the photo edge at odd offsets. On a single screenshot the state looks muddy, not intentional.
- **Hero, desktop.** The headline sits low and left, while the paragraph floats top right. The gap between the two columns and the large empty band above the headline weaken the first fold. The image starts only at y = 395, so the key "ghost" visual is partly below a 900 pixel fold.
- **Hero, mobile.** The two caption lines under the image ("MOVE-OUT PHOTO, LOCKED ONTO THE MOVE-IN PHOTO", "DIFFERENCE VIEW: ONLY REAL CHANGES STAY BRIGHT") stack and look like leftover desktop labels. The "Pan left" pill overlaps the bottom left of the image.
- **Landing, step cards.** The third card ("The proof") is a near-black rectangle with a small white receipt. It is the only dark block among two photos and it reads as a missing image.
- **Landing, evidence band.** Four metric tiles show 0.91, 0.84, 0.35 and "~0.4 s" with small grey captions. The captions are tiny and low contrast. The pipeline list above them sets 11 pixel mono text in five columns.
- **Check page, desktop.** The agent trace panel is a tall grey box with three rows and a large empty area. Below the fold, the page has no content, so a 2400 pixel render is mostly empty beige. The side rail ends after the seal text, which leaves a dead column.
- **Check page, labels.** The long mono callouts ("2 New mark or scratch on the surface") cover the photo and collide with the divider handle on the left callout. They overlap the other marks when two findings sit close.
- **Check page, mobile.** The three-step progress bar and the spot list push the photo below the fold. The signed-report button sits above the work, before the user has done anything.
- **Report, desktop.** The stamp is rotated and lovely, but the title block leaves a wide empty column on the right. The findings tables use very small grey text. Hash rows are 11 pixel mono and unreadable at print scale.
- **Report, mobile.** The stats grid is fine. The before and after pair is cut off at the right edge in the render, which may be the tool width. The reviewer could not confirm it at a true 390 pixel width.
- **Both themes.** The reviewer checked only the light theme. The README claims a dark theme and `progress.md` lists the dark theme check as open.

Three changes that would most raise the score:

1. **Fix the hero fold.** In `landing.css`, tighten the vertical spacing so the image starts near y = 300 on 1440 by 900, and crop the warped ghost to the frame so no wedge shows. Hide the two caption lines on mobile.
2. **Rework the "proof" card and the metric band.** Replace the black card with a real crop of the report stamp and hash rows. Raise caption size to 13 pixels and contrast to AA.
3. **Give the check page a better first view.** Collapse the trace panel to its last three steps, and move the signed-report button to the end of the flow. Place callouts on the photo edge with a leader line, and cap them at one line.

## Factual errors and overclaims

Each item is checked against the code or the source. Fix these before submission.

1. **The $440 breakdown is not in the cited source.** The README, the landing page receipt and the video script show "$250 damage, $125 processing, $65 administration". The Straight Arrow News article mentions "$440 for a scuff on the wheel" and "administrative fees" without amounts. Find a source for the breakdown, or remove the itemised receipt, or label it "illustrative".
2. **"One inch" is not in the source.** The README, the report and the landing page say "a one-inch scuff". The article does not give a size.
3. **"A member of Congress has asked how the system works" is not in the source.** The landing page states it. The fetched article does not mention it. Cite a source or delete the sentence.
4. **"Reviewed by a person: no" and "Nobody looked at it".** The article says reports are sent "without a human ever looking at them", and that staff review only when a customer flags an issue. The receipt label is fair, but "nobody looked" should say "no person reviewed it before the bill".
5. **"A real rental car bill" in the video script.** The receipt on the page is a mock-up built from numbers the source does not give. Do not call it real.
6. **"The move-in set was sealed earlier" for the sample.** The sample check is created and signed when the user clicks the button, with the server key at that moment. It is not a prior seal. Say "sealed when you start the sample".
7. **"Any edit breaks the signature" (landing page) and "the stamp turns green only when every stored photo is re-hashed and signatures check out" (README).** The attack above shows an edit after signing keeps the stamp green. The statement is false until `verify()` compares the manifest with the current state.
8. **"A second signed manifest over all photos, findings and agent traces" (README).** The manifest holds photo hashes, times and, per finding, id, box, verdict, kind and caption. It does not hold the trace or the evidence text.
9. **"Seal 2 ... plus the digest of seal 1" (report section 6).** `manifest()` does not include the other seal. Add it or delete the claim.
10. **"The language model only names changes. Geometry decides every verdict."** The caption step can turn a geometry-confirmed "Changed" finding into "Can't judge", both when the model says `needs_human` and when the Bedrock call fails. The accurate wording is "the model can only name or downgrade a finding, never remove or upgrade one".
11. **"Move-in set is sealed before any move-out photo exists."** The API does not enforce the order. `add_after` works on a check with no seal. Only the web flow enforces it.
12. **"Recall 0.91, precision 0.84, 0.35 false alarms per pair".** These come from the synthetic set with the lenient any-pixel hit rule, thresholds tuned on the same generator. `docs/evaluation.md` does not exist, so nothing in the repo reproduces them. Say "synthetic, lenient match" next to every use, including the landing page tiles.
13. **"Time to compare ~0.4 s" (landing page).** This matches a warm local call (0.33 to 0.42 s for compare only). The same app showed 1.13 s for registration under load, and it has no measurement on Lambda. Label it "on a desktop CPU".
14. **"Five times faster than the classic engine" (video script) and 10.8 against 55.5 ms (README, report).** No script or committed output supports it, and `docs/research.md` records a different earlier pair. Add the script and use its numbers.
15. **"All three bundled samples resolve to their ground truth."** The test checks the car and the room. The desk finding for the coffee ring carries the label "Darker mark or scratch on the surface" and reflection evidence. The desk spot is not asserted in `test_flow.py`.
16. **"Without Bedrock, rule-based labels are used" together with "the agent can label a finding".** The label step is a Claude call only on AWS. In the local run, which judges will see first, every label is a rule string. The demo copy and the hero tags should say so.
17. **Dead references.** `docs/evaluation.md` is linked from the README and the report and does not exist. The report holds the placeholder `EVAL_SUMMARY`. The report line "Live endpoint: see README" points to nothing.
18. **"Photos expire after 30 days" with "Object Lock governance, 1 day".** These can both hold, but the 30 day expiry deletes the evidence a renter may need after a 60 day deposit dispute. State this in the UI at seal time.
19. **"The report states what it cannot prove".** This is accurate and a strength. Keep it. It conflicts with item 7 only until the verify fix lands.

## Ranked top 12 fixes

Ranked by expected score gain per hour of work. Effort: S is under two hours, M is two to six hours, L is over six hours.

1. **Fix the post-signing hole.**
   - What: Make `verify()` rebuild the manifest from current state and compare it with each seal. Reject photo writes after a report seal. Bind seal 2 to the digest of seal 1. Add a regression test.
   - Where: `server/twice/app.py` (`verify`, `run_after`, `run_followup`, `manifest`), `server/tests/test_flow.py`.
   - Why: The product's central promise fails today. Affects the counterparty persona, Gary (correctness), the AWS persona (evidence integrity) and Technical and Impact scores.
   - Effort: S.
2. **Deploy to AWS and publish the URL with proof.**
   - What: Run the SAM deploy, fix first-run failures, keep the stack up, add the URL and the `/api/health` output to the README, and add a CloudWatch screenshot.
   - Where: `deploy/`, `README.md`, `docs/`.
   - Why: A web endpoint and a real AWS component are rules, and Cloud and ops is 10 points. Affects the AWS persona and every rubric line that needs a live demo.
   - Effort: M.
3. **Produce `docs/evaluation.md` with a real-photo set and failure cases.**
   - What: Finish the bench run, write the file, replace `EVAL_SUMMARY`, add 20 to 30 real pairs from two phones, show recall and false alarms with counts, and include at least four honest failures from the gallery.
   - Where: `server/eval/bench.py`, new `server/eval/real.py`, `docs/evaluation.md`, `docs/report.md`.
   - Why: Evaluation evidence including failures is a deliverable. Gary will not believe numbers without it. Affects Technical (30) and Docs (10).
   - Effort: L.
4. **Correct the factual claims about the Hertz case.**
   - What: Find a source for the $250, $125 and $65 breakdown and the Congress statement, or remove them. Drop "one inch" and "real bill" unless sourced. Reword "nobody looked".
   - Where: `web/src/pages/Landing.tsx` lines 130 to 145, `README.md` line 13, `docs/video-script.md`, `docs/report.md`.
   - Why: A judge who checks the source finds a mismatch in the first minute. Affects Phil, Gary and the Impact and Docs scores.
   - Effort: S.
5. **Align the hero labels with real app output, and fix the weak rule labels.**
   - What: Give each sample finding a plain label ("Wall stain", "Coffee ring", "Missing lipstick", "Door scratch") that the app shows, or make the rule captioner use the sample truth. Fix the desk finding that shows reflection evidence under a scratch label.
   - Where: `server/samples/apartment/sample.json`, `server/twice/caption.py`, `web/src/pages/Landing.tsx`.
   - Why: The demo and the video must match what judges see. Affects Phil, the renter and UX.
   - Effort: S.
6. **Make the agent moment the first thing on the sample path.**
   - What: Reorder the sample to start with the car, scroll the follow-up card into view and pulse it once. Show the trace line "vanished under parallax, rule out as glare" in a large sentence, not a mono row.
   - Where: `web/src/pages/CheckPage.tsx`, `web/src/app.css`, `server/samples/apartment/sample.json`.
   - Why: The Agentic Vision award needs a vision result that changes the next action, and judges must see it. Affects Phil, Gary and Innovation.
   - Effort: S.
7. **Add abuse limits and a budget to the AWS stack.**
   - What: Set reserved concurrency, an AWS Budgets alarm and per-check caps on follow-ups and report calls. Store content-addressed photo keys so Object Lock protects what the manifest signs. Fix the S3 key id.
   - Where: `deploy/template.yaml`, `server/twice/app.py`, `server/twice/store.py`.
   - Why: An open Function URL with Bedrock behind it is the first thing an architect attacks. Affects the AWS persona and Cloud and ops.
   - Effort: M.
8. **Add the counterparty acknowledgment and an offline verifier.**
   - What: A button on the move-in link records the other party's receipt in the manifest. Add `tools/verify.py` and link it from the report.
   - Where: `server/twice/app.py`, `web/src/pages/ReportPage.tsx`, new `tools/verify.py`.
   - Why: This is what moves the report from "renter says" to "both sides saw". Affects the counterparty persona, Impact and Innovation.
   - Effort: M.
9. **Add the OpenCV 5 evidence.**
   - What: Commit `server/eval/dnn_engine.py` with 100 timed runs on both engines. Add a table of what is new in 5.0 and where the code uses it. State that the rest is stable 4.x API on 5.0.
   - Where: `server/eval/`, `README.md`, `docs/report.md`.
   - Why: The rules require that OpenCV 5 does the analysis. Gary will look for what is specific to 5. Affects Technical.
   - Effort: S.
10. **Plain-language UI layer and a "keep my link" step.**
   - What: Show sentences first and measurements under a toggle. Replace "Ed25519", "digest" and "z=" in the default view. Add copy, QR and `mailto:` for the link at seal time, plus a note per finding.
   - Where: `web/src/pages/CheckPage.tsx`, `web/src/pages/ReportPage.tsx`, `web/src/app.css`.
   - Why: The renter persona and the non-technical judges stall on jargon. Affects Impact and UX.
   - Effort: M.
11. **Polish the first fold and the weak landing blocks.**
   - What: Pull the hero image up, crop the ghost wedge, hide mobile caption lines, replace the black "proof" card with a real crop, raise metric caption size and contrast, add "synthetic" labels to the metric tiles. Verify at a true 390 pixel width and in dark mode.
   - Where: `web/src/landing.css`, `web/src/components/GhostLock.tsx`, `web/src/pages/Landing.tsx`.
   - Why: The Awwwards juror and the video both start here. Affects UX and first impressions for every persona.
   - Effort: S.
12. **Add a no-camera path and fix the caption failure mode.**
   - What: Let "Start my own" accept two files from disk. When the Bedrock call fails, keep the verdict and use the rule label, and record "label unavailable" in the trace, instead of downgrading to "Can't judge".
   - Where: `web/src/pages/CheckPage.tsx`, `web/src/components/Camera.tsx`, `server/twice/caption.py`, `server/twice/app.py` (`_caption`).
   - Why: Judges on laptops can try their own photos, and a Bedrock outage no longer ruins a demo. Affects Phil, the AWS persona and UX.
   - Effort: M.

## Score outlook

Estimated totals out of 100, using the rubric weights, if nothing changes and if the first six items land.

| Persona | Now | After items 1 to 6 |
|---|---|---|
| Gary Bradski | 51 | 68 |
| Phil Nelson | 62 | 75 |
| AWS architect | 48 | 70 |
| Renter | 64 | 70 |
| Counterparty | 50 | 66 |

The largest swing comes from items 1 and 2. A live endpoint with a verification that holds under attack changes the entry from a polished local demo into a submission that satisfies the rules.
