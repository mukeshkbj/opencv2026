# Twice: demo video script

Target length: 4 min 30 s. Screen recording of the deployed app at 1440 × 900, plus one phone clip.
Voice-over is in plain sentences. Times are cumulative.

## 0:00 to 0:25 — The bill

**Screen:** the landing page `$440` section. Slow scroll over the itemised bill.

**Voice:** "This is the bill one Hertz renter received, line by line. Two hundred and fifty dollars for a one-inch scuff, plus one hundred and ninety in fees. An AI scanner found the scuff. Nobody looked at it. The company has detailed photos. The renter has a phone."

## 0:25 to 0:50 — The idea

**Screen:** scroll up to the hero. Let the ghost-lock animation run once: the ghost slides into place, the frame goes dark, two marks appear, the shadow is tagged "ignored".

**Voice:** "Twice gives the renter the same evidence. Take the same photo twice: once when you move in, once when you move out. Twice lines the two up, finds what really changed, and signs the result."

## 0:50 to 1:40 — Move in, move out, on a phone

**Screen:** phone clip. Press **Start my own**. Shoot one spot; the quality chips turn green and the shutter enables. Seal the set. Then the move-out step: the ghost of the first photo floats over the live camera, the instruction says "Pan left", then "Hold still", and the camera fires on its own.

**Voice:** "At move-in, the shutter waits until the photo is sharp and detailed enough to match later. At move-out, a ghost of the first photo guides you back to the same angle. OpenCV matches every frame to the original with SIFT and a MAGSAC homography, and shoots when it locks."

## 1:40 to 2:50 — The agent at work (sample check)

**Screen:** desktop. Press **Try the sample check**. The car spot opens first. Take the move-out photo. The card above the photo says "The agent needs one more photo. Take one step to the side." Press the button. The dashed box changes to "Reflection · ruled out", and the trace adds `compare_followup: vanished under parallax, rule out as glare`.

**Voice:** "Here is a sealed sample. On the car, a reflection looks like damage. The agent cannot tell from one photo, so it asks for a second one from a step to the side. Reflections move with the camera. Damage stays on the paint. The reflection moved, so it is ruled out. The scratch stayed, so it is reported. A vision result decided the next action."

**Screen:** living room spot. Show the wipe slider, the two "Changed" marks and the dashed "Light change · ruled out" box. Toggle the change map once.

**Voice:** "The living room has a new wall stain and a floor scuff. It also has a shadow that was not there before. A plain image difference flags all three. Twice compares structure and colour in a way that ignores exposure and small shifts, and it checks whether a smooth light field explains the change. The shadow is ruled out."

## 2:50 to 3:30 — The signed report

**Screen:** press **Create the signed report**. Scroll: the green **Verified** stamp, summary counts, exhibit pairs with numbered marks, the findings table with evidence, the hash list, the signatures block. Press **Download evidence bundle**, then cut to a terminal that runs `python verify.py` and prints VALID. Open "What this report cannot prove".

**Voice:** "The report lists every change, every ruled-out shadow, and the evidence behind each one. Every photo is hashed when it arrives. The move-in set was signed before any move-out photo existed. On AWS the signature comes from a KMS key. The evidence bundle carries its own checker, so a landlord or a court can verify it without trusting us. The report also says what it cannot prove."

## 3:30 to 4:05 — Under the hood

**Screen:** the architecture diagram, then the agent loop diagram. Then the README evaluation section.

**Voice:** "Everything runs in one container on Lambda on Graviton. Photos go to S3 with Object Lock. Claude on Bedrock names each change, but it cannot delete one. The object check runs NanoDet on the new OpenCV 5 DNN engine, three and a half times faster than the classic engine on the same CPU. On our synthetic benchmark Twice finds ninety percent of the damage, and ninety-nine percent of its flags are real. On real photos of unchanged scenes, two of twenty-three pairs got a false alarm. The failure cases are in the report."

## 4:05 to 4:30 — Close

**Screen:** back to the hero, final "read" frame with the marks.

**Voice:** "Your next move-out starts with today's photos. Take them twice."

## Shot list

- Landing hero (animation, one full loop) and the `$440` section.
- Phone clip: before capture with quality chips, guided after capture with auto-shutter.
- Sample check: car follow-up and trace, then room result and change map toggle.
- Report: stamp, exhibits, hashes, signatures, limits.
- Diagrams: `docs/diagrams/architecture.png`, `docs/diagrams/agent-loop.png`.
- Terminal: `curl <url>/api/health` showing OpenCV 5.0.0, ENGINE_NEW, the KMS signer and the Bedrock captioner.
