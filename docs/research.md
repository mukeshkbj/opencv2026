# Research notes

## Competition facts
- Deadline: Devpost header says Oct 26, 2026, 11:45 pm PDT; body text says 11:59 pm PT. Treat 11:45 pm as the cutoff.
- Team size: the page says both "up to five" and "no more than four". Use four or fewer.
- Each entry gets at least two independent scores. Tiebreak order: technical execution, then real-world impact.
- Winners are announced Nov 10 on OpenCV Live.

## Crowd (public GitHub repos naming the competition, Oct 22)
About 15 entries are "agent inspects a part and escalates to a human". ClaimLens (insurance photo evidence) is the nearest neighbour to Twice. No entry found for guided re-photography or renter-side evidence.

## Past OpenCV competition winners
- 2021 OAK: 1st Cortic Tigers (education kit), 2nd NeoCam (preterm baby breathing via depth), 3rd Cerebros (EEG wheelchair). Pattern: a human-relatable cause plus sensing that justifies the hardware.
- 2022 Core track: 1st autonomous duckweed collection in Lake Titicaca, 2nd laser 3D scanner, 3rd point-to-read learning system.

## Winning advice (7 sources, see the research agent report)
A problem a non-expert grasps in 10 seconds. A specific person. A live endpoint that works on first click. Real data with failure cases. A video that stands alone, with the pitch in the first seconds.

## OpenCV 5.0.0 facts verified on this machine
- `opencv-contrib-python-headless==5.0.0.93` runs on Python 3.14. CPU only.
- New DNN engine: `cv2.dnn.ENGINE_NEW`, `ENGINE_CLASSIC`, `ENGINE_AUTO`. NanoDet 17–20 ms on the new engine against 57 ms on classic (indicative).
- `cv2.FontFace` TrueType text: `cv2.putText(img, text, org, color, cv2.FontFace("sans"), size)`.
- USAC is the default robust estimator family. `USAC_MAGSAC` homography is about 2x faster than RANSAC on a 200-point set.
- AKAZE, BRISK, KAZE moved to `cv2.xfeatures2d`. SIFT and ORB stay in main.
- calib3d split into `geometry`, `calib`, `stereo`; Python names unchanged.
- opencv.js 5.0.0-pre exists at docs.opencv.org/5.x/opencv.js (16 MB, single-threaded).
- COOL is an AWS Marketplace AMI or container for Graviton only. It cannot run on this machine.

## Hertz hook sources
- https://san.com/cc/car-rental-companys-ai-dent-detection-met-with-customer-frustration/
- https://san.com/cc/how-do-hertzs-ai-damage-scans-work-a-congresswoman-wants-to-know/
- https://www.carscoops.com/2026/04/hertz-ai-ftc-complaint/
Facts: $440 charge for a one-inch wheel scuff ($250 damage, $125 processing, $65 admin). Rep. Nancy Mace letter. Hertz says 97% of scanned cars show no chargeable damage.
