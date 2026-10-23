# Review: Twice submission film

## Creative calls

- The film uses the product's own look: paper #f1eee7, Gambetta, Switzer, JetBrains Mono and the signal red. The spec bans a cream ground with a serif display by default. The brand uses exactly that, so the film follows the brand.
- One storyline only, because the run had no stops: the bill, the idea, the product working, the proof, the numbers. The narration was written and voiced earlier (`video/narration.json`).
- The product screens play full frame. Graphics appear only where no screen exists: the receipt, the terminal, the diagram tour and the numbers.
- No music. The music library needs a HeyGen sign-in that this machine does not have. The voice runs over every scene, so the film is not silent.

## Footage cuts

All clips come from the local app at 1440 × 810, converted to constant 30 fps (`video/footage/*_cfr.mp4`), then cut. `r4_flow` is the second take, recorded after judge round 4 (ghost guide in the sample, named findings, zoomed crops).

| Clip | Source | In (s) | Length (s) | Speed |
|---|---|---|---|---|
| hero | r1_landing | 0.5 | 13 | 1× |
| steps | r3_steps | 6.5 | 6.4 | 1× |
| guide | r4_flow | 12.0 | 8.0 | 1× |
| car_a | r4_flow | 20.0 | 2.0 | 0.29× (the side-step request holds still) |
| car_b | r4_flow | 22.0 | 10.6 | 0.91× |
| room | r4_flow | 32.6 | 18.9 | 1.11× |
| report | r4_flow | 61.9 | 20 | 1.57× |

Scenes 3 to 5 zoom the main column 1.4× and scene 6 zooms the report 1.35×, so the UI text reads at 1080p.

## Second pass, after judge round 4

- S1 has a shorter voice line (15.9 s, was 18.7 s), so the product appears at 0:17.
- S3 now ends on the real ghost guide in the sample check.
- S4 and S5 show the zoomed finding crops.
- S9 shows "90%" at 1.2 s instead of 2.9 s, so the scene no longer opens on an empty frame.

## Third pass, after the engine change

- S9 has new numbers from the plain first-pass engine: 88%, 100% and 0 of 22. The voice line was regenerated (14.9 s, was 15.4 s). The beats keep their times.
- The S4 car footage still shows the earlier wipe position and evidence text. It was not re-recorded.

## What was measured and what was only looked at

- `npx hyperframes check` passes with no errors.
- I looked at the review sheets (beats, seams, phone width) and at snapshots of every changed moment.
- Nobody listened to the mix. The voice files were transcribed with Parakeet and the transcripts match the script.

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
