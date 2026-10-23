# Review: Twice submission film

## Creative calls

- The film uses the product's own look: paper #f1eee7, Gambetta, Switzer, JetBrains Mono and the signal red. The spec bans a cream ground with a serif display by default. The brand uses exactly that, so the film follows the brand.
- One storyline only, because the run had no stops: the bill, the idea, the product working, the proof, the numbers. The narration was written and voiced earlier (`video/narration.json`).
- The product screens play full frame. Graphics appear only where no screen exists: the receipt, the terminal, the diagram tour and the numbers.
- No music. The music library needs a HeyGen sign-in that this machine does not have. The voice runs over every scene, so the film is not silent.

## Footage cuts

All clips come from the local app at 1440 × 810, converted to constant 30 fps (`video/footage/*_cfr.mp4`), then cut:

| Clip | Source | In (s) | Length (s) | Speed |
|---|---|---|---|---|
| hero | r1_landing | 0.5 | 13 | 1× |
| steps | r3_steps | 6.5 | 15 | 1× |
| car | r2_flow | 13 | 12.7 | 0.683× |
| room | r2_flow | 25.8 | 12.8 | 0.75× |
| report | r2_flow | 47.2 | 19 | 1.5× |

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

S9, the numbers. It is type on paper. With more time, each number would come out of the product: the 90% from the evaluation gallery, the 22 squares as the 22 real photo pairs.
