# Twice: demo video script

The final film is 1 min 40 s at 1920 × 1080 and 30 fps. It is a HyperFrames project in `video/twice-demo`. The voice is Kokoro (af_heart), generated on this machine. The music is our own, composed in code by `video/twice-demo/score.py`. The sound effects come from the earshot sound bank. Captions are burned in for muted viewing. App footage is a screen recording of the local app at 1440 × 810. The terminal output is real `verify.py` output from a downloaded bundle.

Times are cumulative.

## 0:00 to 0:07 — The question

**Screen:** the real car photo, full frame. A red box marked "A ?" lands on the scratch. A second box marked "B ?" lands on the reflection.

**Voice:** "One of these marks is a scratch. The other is just a reflection. Can you tell which one you would pay for?"

## 0:07 to 0:22 — The bill

**Screen:** a printed receipt. A red "No human review" stamp lands on it. Then two lines replace the text: the company has an AI scanner; the renter has a phone.

**Voice:** "One Hertz renter got a four hundred and forty dollar bill for a one-inch scuff, minutes after returning the car. A House subcommittee chair says Hertz bills from these scans without human review. The company has an AI scanner. The renter has a phone."

## 0:22 to 0:28 — The idea

**Screen:** the landing page. The hero locks the move-out photo onto the move-in photo.

**Voice:** "Twice gives the renter proof. Take the same photo twice: when you move in, and when you move out."

## 0:28 to 0:36 — The ghost guide

**Screen:** the sample check. The ghost of the move-in photo glides into lock, and the shutter fires.

**Voice:** "At move-out, a ghost of your first photo walks you back to the exact spot. The shutter fires when OpenCV locks on."

## 0:36 to 0:50 — The answer

**Screen:** the car spot at 1.4× zoom. The agent asks for a side-step photo. The reflection is ruled out. The camera pans down to the scratch, which stays.

**Voice:** "So: scratch, or reflection? One photo cannot tell. Twice asks for one more, from a step to the side. The reflection slides away. The scratch stays put."

## 0:50 to 0:59 — The living room

**Screen:** the living room spot at 1.4× zoom, with the shadow ruled out and the stain and scuff marked.

**Voice:** "In the living room, the new shadow is ruled out. The stain and the scuff stay."

## 0:59 to 1:06 — The report

**Screen:** the signed report, scrolled at about 1.7× speed.

**Voice:** "Every finding lands in a signed report. The move-in photos were sealed before the move-out photos existed."

## 1:06 to 1:12 — Anyone can check it

**Screen:** a terminal. `python verify.py` prints VALID. One byte is added to a photo, and the next run prints NOT VALID. The music stops.

**Voice:** "Anyone can check it, without trusting us. Change one byte, and the check fails."

## 1:12 to 1:22 — How it runs

**Screen:** the architecture diagram, then two bars with the measured NanoDet time: 16.3 ms on `ENGINE_NEW`, 56.5 ms on `ENGINE_CLASSIC`.

**Voice:** "OpenCV 5 does the vision, on AWS. Object detection runs on the new DNN engine, more than three times faster than the classic one."

## 1:22 to 1:33 — The numbers

**Screen:** one number at a time: 88%, 100%, then "0 of 22" with 22 squares.

**Voice:** "On our benchmark, Twice finds eighty-eight percent of the damage, and every flag is real. On twenty-two real photo pairs of unchanged scenes: zero false alarms."

## 1:33 to 1:40 — Close

**Screen:** "Take them twice."

**Voice:** "Your next move-out starts with today's photos. Take them twice."

## Rebuild

```bash
cd video/twice-demo
C:/Users/mukes/tools/earshot/.venv/Scripts/python.exe score.py   # music and sound effects
npx hyperframes check
npx hyperframes render -o renders/twice-demo.mp4
ffmpeg -i renders/twice-demo.mp4 -c:v copy -af loudnorm=I=-14:TP=-1.0:LRA=7 -c:a aac -b:a 192k ../../docs/video/twice-demo.mp4
```

The voice lines are in `video/narration_v2.json`. The footage cuts and their source times are in `video/twice-demo/REVIEW.md`.
