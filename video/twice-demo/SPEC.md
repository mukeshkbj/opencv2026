# Twice: submission film

GOAL:    A judge who has never seen Twice can say what it does, why a renter needs it, and why the proof holds, after one viewing.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps.
TIME:    149.8 s x 30 = 4494 frames. Voice-led (Kokoro af_heart). No music: the music library needs a HeyGen sign-in that this machine does not have.
LOOK:    The product's own system, taken from `web/src`. Ground #f1eee7 paper, flat, no texture. Ink #17160f. One accent, signal #e2401a, on one element per shot (the stamp, the italic "twice", the failing line, the faster bar). Display Gambetta 400 at 120-200 px, tracking -2%. Body Switzer 500 at 34-44 px. Data JetBrains Mono 400 at 26-30 px. Product screens fill the frame edge to edge.
OBJECTS: A printed rental receipt (white, 1 px hairline, zigzag tear at the foot, 0 18 40 rgb(23 22 15 / 0.12) shadow). A rubber stamp in signal red, 6 px border, rotated -7 deg. A terminal window (#17160f, title bar with three dots). The architecture diagram from `docs/diagrams`.
MOTION:  Arrivals expo.out 0.5-0.7 s. Camera moves power2.inOut 0.9-1.2 s. Exits power3.in 0.25 s. The stamp lands in 0.18 s (scale 1.6 to 1, power4.out). Lines of text land, then hold still.
SHOTS:
  S1   0.0-19.6  The receipt prints line by line as the voice reads each charge. "No human review" stamps onto it at "without human review". Two lines replace it: the company has an AI scanner; the renter has a phone.
  S2  19.6-32.1  Landing page: the hero locks the move-out photo onto the move-in photo.
  S3  32.1-46.5  Landing steps section. Camera pushes onto the quality chips, then pans to the ghost card at "ghost".
  S4  46.5-65.1  Sample check, car: reflection, side-step request, ruled out. Push onto the result at "ruled out".
  S5  65.1-82.2  Sample check, living room: change map toggles on and off.
  S6  82.2-94.9  Signed report scroll, 1.5x.
  S7  94.9-104.9 Terminal: real verify.py output, VALID, then one byte added to a photo, NOT VALID in red.
  S8 104.9-127.1 Architecture diagram tour: Lambda, S3, KMS, Bedrock, the DNN row; then measured bars, ENGINE_NEW 16.3 ms vs ENGINE_CLASSIC 56.5 ms.
  S9 127.1-143.4 One number per beat on one stage: 90%, 99%, 2 of 22.
  S10 143.4-149.8 "Take them twice."
BANNED:  dark void grounds, glow, gradients, glass cards, three cards in a row, KPI grids, corner labels, everything fading up at once, text that moves while it is read, a logo end card, numbers that are not in docs/evaluation.md.
QA:      t=9.9 receipt total visible; t=14.9 stamp on; t=63 push onto car result; t=101 terminal VALID; t=104.5 NOT VALID; t=125 bars; t=137 "2 of 22"; t=149 end line.
