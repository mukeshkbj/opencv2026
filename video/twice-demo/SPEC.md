# Twice: submission film

GOAL:    A judge who has never seen Twice can say what it does, why a renter needs it, and why the proof holds, after one viewing.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps.
TIME:    147 s x 30 = 4410 frames. Voice-led (Kokoro af_heart). No music: the music library needs a HeyGen sign-in that this machine does not have.
LOOK:    The product's own system, taken from `web/src`. Ground #f1eee7 paper, flat, no texture. Ink #17160f. One accent, signal #e2401a, on one element per shot (the stamp, the italic "twice", the failing line, the faster bar). Display Gambetta 400 at 120-200 px, tracking -2%. Body Switzer 500 at 34-44 px. Data JetBrains Mono 400 at 26-30 px. Product screens fill the frame edge to edge.
OBJECTS: A printed rental receipt (white, 1 px hairline, zigzag tear at the foot, 0 18 40 rgb(23 22 15 / 0.12) shadow). A rubber stamp in signal red, 6 px border, rotated -7 deg. A terminal window (#17160f, title bar with three dots). The architecture diagram from `docs/diagrams`.
MOTION:  Arrivals expo.out 0.5-0.7 s. Camera moves power2.inOut 0.9-1.2 s. Exits power3.in 0.25 s. The stamp lands in 0.18 s (scale 1.6 to 1, power4.out). Lines of text land, then hold still.
SHOTS:
  S1   0.0-16.8  The receipt prints as the voice reads the total. "No human review" stamps onto it at "without human review". Two lines replace the text: the company has an AI scanner; the renter has a phone.
  S2  16.8-29.3  Landing page: the hero locks the move-out photo onto the move-in photo.
  S3  29.3-43.7  Landing steps section, push onto the quality chips. Cut at 6.4 s to the sample check: the ghost glides into lock and the shutter fires.
  S4  43.7-62.3  Sample check, car, 1.4x: side-step request, reflection ruled out, scratch kept, scroll to the zoomed crop.
  S5  62.3-79.4  Sample check, living room, 1.4x: change map on and off, scroll to the stain and scuff crops.
  S6  79.4-92.1  Signed report, 1.35x zoom, about 1.6x speed.
  S7  92.1-102.1 Terminal: real verify.py output, VALID, then one byte added to a photo, NOT VALID in red.
  S8 102.1-124.3 Architecture diagram tour: Lambda, S3, KMS, Bedrock, the DNN row; then measured bars, ENGINE_NEW 16.3 ms vs ENGINE_CLASSIC 56.5 ms.
  S9 124.3-140.6 One number per beat on one stage: 88%, 100%, 0 of 22.
  S10 140.6-147.0 "Take them twice."
BANNED:  dark void grounds, glow, gradients, glass cards, three cards in a row, KPI grids, corner labels, everything fading up at once, text that moves while it is read, a logo end card, numbers that are not in docs/evaluation.md.
QA:      t=5.8 receipt total visible; t=11.3 stamp on; t=37 ghost guide; t=57 car crop; t=70 change map; t=98 terminal VALID; t=101.6 NOT VALID; t=122 bars; t=134 "0 of 22"; t=146 end line.
