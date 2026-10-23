# Twice: demo video script

The final film is 2 min 27 s at 1920 × 1080 and 30 fps. It is a HyperFrames project in `video/twice-demo`. The voice is Kokoro (af_heart), generated on this machine. The film has no music. App footage is a screen recording of the local app at 1440 × 810. The terminal output is real `verify.py` output from a downloaded bundle.

Times are cumulative.

## 0:00 to 0:17 — The bill

**Screen:** a printed receipt. The charges print as the voice reads the total. A red "No human review" stamp lands on it. Then two lines replace the text on the right.

**Voice:** "One Hertz renter got this bill minutes after returning a car. Four hundred and forty dollars, for a one-inch scuff on a wheel. A House subcommittee chair says Hertz sends these bills without human review. The company has an AI scanner. The renter has a phone."

## 0:17 to 0:29 — The idea

**Screen:** the landing page. The hero locks the move-out photo onto the move-in photo and marks the two changes.

**Voice:** "Twice gives the renter the same evidence. Take the same photo twice: when you move in, and when you move out. Twice lines the two photos up, finds what really changed, and signs the proof."

## 0:29 to 0:44 — Move in, move out

**Screen:** the landing page steps, with a push onto the quality chips. Then the sample check: the ghost of the move-in photo glides into lock, the HUD says "Pan left", "Move closer", "Locked", and the shutter fires.

**Voice:** "At move-in, the shutter waits until each photo is sharp and detailed enough to match months later. At move-out, a ghost of the first photo guides you back to the same angle, and the camera fires when OpenCV locks on."

## 0:44 to 1:02 — The car

**Screen:** the car spot at 1.4× zoom. The agent asks for a side-step photo. The reflection is ruled out and the scratch stays. The page scrolls to the finding and its zoomed move-in and move-out crop.

**Voice:** "Here is a sample check. On the car, a reflection looks like damage. One photo cannot tell them apart, so the agent asks for one more, from a step to the side. A reflection moves with the camera. A scratch stays on the paint. So the reflection is ruled out, and the scratch is reported."

## 1:02 to 1:19 — The living room

**Screen:** the living room spot at 1.4× zoom. The change map turns on, then off. The page scrolls to the stain and scuff crops.

**Voice:** "In the living room, a plain image difference would also flag the new shadow. Twice compares structure and colour, ignores exposure and small shifts, and tests whether a smooth change of light explains the difference. The shadow is ruled out. The stain and the scuff stay."

## 1:19 to 1:32 — The report

**Screen:** the signed report at 1.35× zoom, scrolled at about 1.6× speed.

**Voice:** "The report shows every change, every ruled-out shadow, and the measurements behind each one. Every photo is hashed on arrival, and the move-in set is signed before any move-out photo exists."

## 1:32 to 1:42 — Anyone can check it

**Screen:** a terminal. `python verify.py` prints VALID. One byte is added to a photo, and the next run prints NOT VALID.

**Voice:** "Anyone can download the evidence bundle and check it with the script inside, without trusting our server. Change one photo, and the check fails."

## 1:42 to 2:04 — How it runs

**Screen:** the architecture diagram. The camera visits Lambda, S3, KMS, Bedrock and the DNN row. Two bars show the measured NanoDet time: 16.3 ms on `ENGINE_NEW`, 56.5 ms on `ENGINE_CLASSIC`.

**Voice:** "Twice runs in one container on AWS Lambda. Photos go to S3 with Object Lock, and a KMS key signs every report. Claude on Bedrock names each change, but it can never delete one. Objects are checked with NanoDet on the new OpenCV 5 DNN engine, more than three times faster than the classic engine."

## 2:04 to 2:21 — The numbers

**Screen:** one number at a time: 90%, 99%, then "2 of 22" with 22 squares, two of them red.

**Voice:** "On our synthetic benchmark, Twice finds ninety percent of the damage, and ninety-nine percent of its flags are real. On real photos of unchanged scenes, two of twenty-two judged pairs got a false alarm. Every failure case is in the report."

## 2:21 to 2:27 — Close

**Screen:** "Take them twice."

**Voice:** "Your next move-out starts with today's photos. Take them twice."

## Rebuild

```bash
cd video/twice-demo
npx hyperframes check
npx hyperframes render -o renders/twice-demo.mp4
```

The voice lines are in `video/narration.json`. The footage cuts and their source times are in `video/twice-demo/REVIEW.md`.
