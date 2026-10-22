# Idea candidates (round 1)

## A. Alibi: before/after condition evidence for anything you rent
A renter films an apartment or rental car at pickup. They film it again at return. The system aligns the two captures and finds the new damage, with proof. An agent watches the live capture. It asks for a re-shot when a frame is blurred or dark, or when an area has no coverage. It asks for a close-up when it finds a candidate change.
- Hook: Hertz's AI scanners bill renters $440 for a one-inch scuff, with no human review. Renters have no AI of their own.
- OpenCV 5: Laplacian sharpness, exposure checks, SIFT/ORB features, USAC MAGSAC homography, DIS optical flow refinement, CLAHE illumination normalization, structural difference, morphology, contours.
- Agent loop: vision output decides "accept frame", "re-shoot", "close-up on region R", "escalate to human".
- AWS: Bedrock for the verifier and agent, S3 evidence vault with hashes, Lambda or Fargate Graviton for the pipeline.
- Demo: a judge captures their desk, moves a mug, captures again. The change appears. Instant.

## B. Pill check for caregivers
Phone camera counts and verifies pills on a tray against a prescription (count, color, shape). Agent asks the user to spread or flip pills for imprint reading.
- Impact: medication errors. Relatable for people who care for parents.
- Risk: medical liability. Demo data needs real pills.

## C. Wound tracker
Phone photos of chronic wounds with a printed ArUco/color card. Accurate area and color tracking over weeks. Agent asks for a re-take when the angle or light is wrong.
- Impact: real clinical gap (ruler measurement error is large).
- Risk: sensitive images, not instantly relatable, no demo data.

## D. Visual troubleshooter for home appliances
Point a camera at a device; an agent reads lights and displays and guides repair.
- Risk: mostly LLM; OpenCV depth is thin.
