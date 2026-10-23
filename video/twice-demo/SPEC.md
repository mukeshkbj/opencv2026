# Twice: submission film (storyline A, "Scratch or reflection?")

GOAL:    In the first five seconds a judge sees the product's hardest case as a question they cannot answer. After one viewing they can say what Twice does, why a renter needs it, and why the proof holds.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps.
TIME:    100 s x 30 = 3000 frames. Voice-led (Kokoro af_heart, speed 1.06, lines in video/narration_v2.json).
SOUND:   Our own music, composed in code by score.py at 105 bpm in A minor and ducked 10 dB under the voice. Sound effects come from the earshot bank (earshot sfx render). First sound at 0.03 s. One riser into the reflection beat (42.4 s). One stop-down plus impact on NOT VALID (69.8 s). One resolving hit on "Take them twice" (96.0 s). Delivered at -16 LUFS, true peak -1.5 dBTP.
CAPTIONS: Burned in for muted viewing. 3 to 7 words a group, Switzer 500 52 px, ink on a 94% paper pill, 96 px from the bottom. No captions where the screen already shows the words (the numbers, the end line, "3.5x faster").
LOOK:    The product's own system, taken from `web/src`. Ground #f1eee7 paper, flat. Ink #17160f. One accent, signal #e2401a, on one element per shot. Display Gambetta 400, body Switzer 500, data JetBrains Mono 400. Product screens fill the frame.
MOTION:  Arrivals expo.out 0.5-0.7 s. Camera moves power2.inOut 1.0 s. The red question boxes and the stamp land in 0.18 s (scale 1.25 or 1.6 to 1, power4.out). Text lands, then holds still.
SHOTS:
  A0   0.0-6.6   The real car photo full-bleed. Box "A ?" lands on the scratch at "scratch", box "B ?" on the reflection at "reflection". Slow push to 1.06.
  S1   6.6-21.8  The receipt prints; "No human review" stamps at 16.6 s. Then: the company has an AI scanner; the renter has a phone.
  S2  21.8-27.6  Landing hero locks the move-out photo onto the move-in photo. The music opens up.
  S3  27.6-35.6  Sample check: the ghost glides into lock; the shutter fires at 31.6 s.
  S4  35.6-49.6  Car at 1.4x: the side-step request, the reflection ruled out, a pan down to the kept scratch.
  S5  49.6-58.6  Living room at 1.4x: the shadow ruled out, the stain and the scuff kept.
  S6  58.6-65.8  Signed report at about 1.7x speed.
  S7  65.8-71.6  Terminal: real verify.py output, VALID, one byte added, NOT VALID with a shake. The music stops.
  S8  71.6-82.2  Architecture tour, then the measured bars, ENGINE_NEW 16.3 ms vs ENGINE_CLASSIC 56.5 ms.
  S9  82.2-93.4  One number per beat: 88%, 100%, 0 of 22.
  S10 93.4-100.0 "Take them twice."
BANNED:  dark void grounds, glow, gradients, glass cards, three cards in a row, KPI grids, a logo end card, numbers that are not in docs/evaluation.md, stock music.
QA:      t=2 box A; t=4 box B; t=16.7 stamp; t=31.6 shutter flash; t=44 scratch kept; t=52 room; t=67.6 VALID; t=70.2 NOT VALID; t=80 bars; t=88.5 "0 of 22"; t=97 end line.
