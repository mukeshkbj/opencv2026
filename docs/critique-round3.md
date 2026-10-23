# Persona critique, round 3

This round reviews the finished product as three judges: an OpenCV core developer, an AWS solutions architect and a consumer-product founder. Each judge scored the rubric and named the changes that would raise the score most. A separate code review checked the retake rule, the evidence bundle and the offline verifier.

## Code review findings and outcomes

| Finding | Outcome |
| --- | --- |
| `verify.py` printed VALID for a bundle whose report seal was removed | It now says when a bundle holds only the move-in set. A test covers a missing move-in seal and a missing report seal |
| The view check read only the affine part of the homography at pixel (0, 0), so a strong tilt could pass | The check now measures local scale and stretch at the centre and the four corners and rejects mirror images (`tests/test_vision.py`) |
| Two resolutions of the same view failed the scale bound | Scale is normalised by the image sizes |
| `verify.py` built a file path from an unverified hash | Hashes must be 64 hex characters |
| The bundle could include unsigned photos and duplicate entries | It ships each signed photo once |
| The real-photo benchmark did not count every retake reason | It counts all reasons |

The review run also showed that the agent benchmark was not reproducible: RANSAC uses OpenCV's global random generator. The benchmark now seeds it and runs every pair under 5 seeds.

## Judge findings and outcomes

| Finding | Outcome |
| --- | --- |
| "Nobody looked at it before the bill went out" is not in The Drive's article | Replaced with what the sources say: the bill came minutes after the return, and the subcommittee chair's letter says Hertz is the only rental company that issues these assessments without human review. Repairer Driven News added as a source |
| The $250, $125 and $65 split and the one-inch scuff need a source | Both are in The Drive's article: "$250 for the repair, $125 for processing, and another $65 administrative fee", "a 1-inch scuff on the driver's side rear wheel" |
| The report does not say which parts need OpenCV 5 | Report section 4 now says that the DNN `ENGINE_NEW` is the OpenCV 5 part and that the other calls also exist in OpenCV 4 |
| Lenient recall is the headline | The README quotes the strict engine-level recall (0.74) next to it |
| Landing tiles and latency lack labels | The note under the tiles starts with "Synthetic benchmark" and says the compare time is on a desktop CPU |
| "About one second at 3 GB" on Lambda is not measured | The report says the Lambda time is not measured and gives the one-thread desktop figure |
| Reserved concurrency of 10 may throttle the live guide | Each camera waits for one guide answer before it sends the next frame, so one user holds one execution. The report says the cap serves about ten users and where to raise it |
| "Sealed earlier" is wrong for the sample | The README says the sample seals the photos when it starts |
| No next step for "Can't judge" | The report now tells the reader to look at those photos with the other party before anyone pays |
| A laptop judge cannot use the camera | Every camera step already has an upload button; the README now says so |
| Round 2 critique still reads as open | It now starts with a status line |

## Open

- **No live endpoint.** The AWS deploy needs credentials that this machine does not have. The owner runs `deploy/deploy.sh` and adds the Function URL and the `/api/health` output to the README.
- **No labelled real damage.** The real-photo benchmark measures false alarms only.
