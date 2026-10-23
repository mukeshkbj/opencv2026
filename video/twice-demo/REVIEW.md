# Review: Twice submission film

## Creative calls

- The film uses the product's own look: paper #f1eee7, Gambetta, Switzer, JetBrains Mono and the signal red. The spec bans a cream ground with a serif display by default. The brand uses exactly that, so the film follows the brand.
- The fourth pass follows storyline A from `STORYLINES.md`, which the owner chose: the film opens on the product's hardest case as a question (scratch or reflection?) and answers it in S4. The narration is `video/narration_v2.json`.
- The product screens play full frame. Graphics appear only where no screen exists: the receipt, the terminal, the diagram tour and the numbers.
- The music is composed in code (`score.py`), because the HeyGen music library needs a sign-in. The sound effects are earshot bank sounds, placed on the visible actions.

## Footage cuts

All clips come from the local app at 1440 × 810, converted to constant 30 fps (`video/footage/*_cfr.mp4`), then cut. `r5_flow` is the third take, recorded after judge round 5 (wipe starts left of the first changed mark, plain evidence sentences, plain first-pass engine).

| Clip | Source | In (s) | Length (s) | Speed |
|---|---|---|---|---|
| hero | r1_landing | 0.5 | 13 | 1× |
| steps | r3_steps | 6.5 | 6.4 | 1× |
| guide | r5_flow | 11.1 | 8.0 | 1× |
| car_a | r5_flow | 19.2 | 2.0 | 0.29× (the side-step request holds still) |
| car_b | r5_flow | 21.6 | 10.6 | 0.91× |
| room2 | r5_flow | 34.4 | 12.1 | 1.34× |
| report2 | r5_flow | 61.5 | 12.0 | 1.67× |

The fourth pass uses hero for 5.8 s, drops steps, and replaces room and report with room2 and report2.

Scenes 3 to 5 zoom the main column 1.4× and scene 6 zooms the report 1.35×, so the UI text reads at 1080p.

## Second pass, after judge round 4

- S1 has a shorter voice line (15.9 s, was 18.7 s), so the product appears at 0:17.
- S3 now ends on the real ghost guide in the sample check.
- S4 and S5 show the zoomed finding crops.
- S9 shows "90%" at 1.2 s instead of 2.9 s, so the scene no longer opens on an empty frame.

## Third pass, after the engine change

- S9 has new numbers from the plain first-pass engine: 88%, 100% and 0 of 22. The voice line was regenerated (14.9 s, was 15.4 s). The beats keep their times.
- S3 to S6 use a new take (`r5_flow`): the car scratch now sits on the move-out side of the wipe, and the findings and report show the plain evidence sentences.

## Fourth pass, storyline A (100 s)

- A0 cold open: the real car photo with two red question boxes, in sync with the voice.
- Every scene is shorter. The film is 100 s (was 147 s).
- Music, sound effects and burned-in captions are new.

## What was measured and what was only looked at

- `npx hyperframes check` passes with no errors. One craft warning (the s9 footer hold) was fixed.
- I looked at snapshots of every changed moment and at frames from the rendered MP4.
- No person listened to the mix. `earshot critique` scores it launch-grade: 22 of 23 metrics in range against 7 reference launch films, -14.3 LUFS, true peak -0.9 dBTP. The one metric out of range is stereo width (-21.8 dB side against mid), because the voice is mono.
- The `earshot sheet` showed that the opening sub bass was too loud and that the cut at 82.2 s had no sound. Both are fixed.
- Whisper (small.en) transcribes the final mix the same as the voice alone. With the music ducked 7 dB, "shutter" came back as "shut", so the duck is now 9 dB. "existed" (64.6 s) is lost in both versions, so the speech recogniser causes it, not the music.

## Fixed during review

- S3, S4 and S6 opened on the wrong page (landing hero, landing page, desk page). The in-points moved.
- S1: the stamp covered the total, the receipt had empty space, and the two closing lines collided.
- S9 opened on an empty frame for 2.9 s. The source line now appears first.
- "56.5 ms" wrapped under its bar.

## Kept on purpose

- `dead_stretch` at 5.3 to 8.5 s: the receipt holds still while the voice reads the charge. The underline under the scuff line is the only change there.
- The S8 bar panel covers the lower half of the diagram. The diagram row it explains stays visible above it.

## Weakest shot

S9, the numbers. It is type on paper. With more time, each number would come out of the product: the 88% from the evaluation gallery, the 22 squares as the 22 real photo pairs.
