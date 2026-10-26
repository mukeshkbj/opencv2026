# Agentic Vision with OpenCV 5: evidence

Twice is a perception-decision-action loop. OpenCV 5 measures a pair of photos. The agent reads those measurements and picks the next action: rule a region out, report it, ask the renter for one more photo, or hand the region to a person. Each new photo goes back through OpenCV 5, and its result decides the next step again.

This page maps each item the award asks for to the evidence in this repository.

## 1. Workflow diagram

![Agent loop: perception, decision, action](diagrams/agent-loop.png)

| Stage | What runs | Code |
|---|---|---|
| Perception | SIFT, FLANN, `findHomography` (`USAC_MAGSAC`), `warpPerspective`, `DISOpticalFlow`, a structure and colour z-score map, `connectedComponentsWithStats`, NanoDet on `cv2.dnn.ENGINE_NEW` | `server/twice/vision.py`, `server/twice/objects.py` |
| Decision | A rule planner with a budget of two follow-up photos per spot. Each tool result selects the next tool call. | `server/twice/agent.py` |
| Action | Ask for a retake, a side-step photo or a close-up. Rule out, report, or mark "can't judge". Caption with Claude on Bedrock, then sign the report with KMS. | `server/twice/agent.py`, `server/twice/app.py` |

The source of the diagram is `docs/diagrams/agent-loop.html`.

## 2. A trace where OpenCV output changes the next action

`cd server && python -m eval.trace` drives the bundled sample check through the real API and writes [eval/agent-trace.md](eval/agent-trace.md). These are the car rows:

| # | Tool | OpenCV result | Decision |
|---|---|---|---|
| 3 | `glare_check` | f1: specular change +12% | needs a parallax shot |
| 6 | `plan` | f1 unresolved | request parallax photo |
| 7 | `compare_followup` | f1: vanished after the camera moved 2.5% | rule out as glare |

The near-white share of the region grew by 12%. That measurement is the only reason the agent asks for a side-step photo. The side-step photo goes back through registration and the change map. The mark is gone, so the agent rules it out as a reflection. The scratch next to it stays, because the same measurements call it a surface change.

The same script runs a counterfactual. The request is the same, but the renter does not move for the side-step photo:

| # | Tool | OpenCV result | Decision |
|---|---|---|---|
| 7 | `parallax_check` | f1: camera moved 0.0% of the frame, under 1% | ask again, a full step to the side |
| 9 | `parallax_check` | f1: camera moved 0.0% of the frame, under 1% | ask again, a full step to the side |
| 10 | `budget` | f1: no follow-ups left | mark cannot judge |

Only the visual evidence differs between the two runs, and the agent's actions differ. The homography of the side-step photo shows that the camera did not move. A photo from the same place cannot separate a reflection from damage, so the agent asks again, with a firmer prompt. When the budget is spent, a person decides. Before this check, the same input produced a false damage finding. The test `test_side_step_from_the_same_place_is_not_evidence` keeps the behaviour.

Every live check stores the same trace. The app shows it under "How it decided", and the signed report includes it, so a changed trace breaks the signature.

## 3. Evaluation

### Task success

`server/eval/agent_bench.py` runs the full loop on 170 synthetic pairs under 5 RANSAC seeds (850 runs). When the agent asks for a photo, the benchmark makes one: a new camera position for a side-step request, or a tighter crop for a close-up. A run succeeds when the agent finds every defect and reports no false change.

| Set | Runs | Successful runs |
|---|---|---|
| Damage | 400 | 316 (79%) |
| No change | 150 | 145 (97%) |
| Exposure | 75 | 75 (100%) |
| Colour temperature | 75 | 75 (100%) |
| Cast shadow | 75 | 73 (97%) |
| Reflection (specular highlight) | 75 | 70 (93%) |
| **All** | **850** | **754 (89%)** |

Defect recall is 0.88 and precision is 1.00. The engine alone, without the loop, flags all 15 reflection pairs as damage. The agent asked for a side-step photo in 70 of the 75 reflection runs, and all 70 ended correctly. The 5 runs where the agent did not ask all failed. The loop asked for 174 follow-up photos in 850 runs (122 side-step, 52 close-up), never more than two for one spot.

On real photos of unchanged scenes (`server/eval/real_bench.py`, the Oxford affine sequences), none of the 22 judged pairs got a false alarm. The method and the failure gallery are in [evaluation.md](evaluation.md).

### Failure handling

| Failure | What the agent does | Where |
|---|---|---|
| The move-out photo does not register (fewer than 25 inliers, an implausible homography, or a view too far from the first one) | Asks for a retake from the same spot. On the real photo set, this happened for 18 of 40 pairs: 10 views were too far away, 8 did not match. | `register` in `agent.py`; `real_bench.py` |
| A follow-up photo does not register | Marks the finding "can't judge". | `compare_followup` |
| The side-step photo was taken from the same place | Asks again with a firmer prompt, then marks "can't judge". | `parallax_check` |
| The budget of two follow-ups is spent | Marks every unresolved finding "can't judge". | `budget` |
| A person stands over a finding in only the move-out photo | Marks it "can't judge" and asks for a retake without people. | `object_check` |
| Bedrock fails or cannot name the change | Uses the rule label, or adds a note for a human reviewer. | `caption.py` |

### Observability

- **Trace:** every tool call is logged with the measurement that caused it and the decision it led to. The app shows the trace, and the report signs it.
- **Metrics:** CloudWatch embedded metrics in the `Twice` namespace: `CompareLatency` and `GuideLatency` in milliseconds, and `AgentDecision` with a `Tool` dimension, one count per decision. Follow-up, retake and "can't judge" rates come straight from `AgentDecision`.
- **Logs and alarm:** the SAM template creates a log group with 14-day retention and an alarm on Lambda errors (`deploy/template.yaml`).
- **Health:** `GET /api/health` reports the OpenCV version and build, the CPU architecture, the signer and the captioner.

### Human control

- The renter takes every photo. The agent only asks, and it explains why: "Take one step to the side and shoot this spot again. Reflections move, damage stays."
- "Can't judge" is a real answer. The report asks a person to review every "Changed" and "Can't judge" item.
- The language model only names changes. It can flag a finding for a human, but it cannot add, delete or change a verdict. Geometry and measurement decide every verdict.
- The budget caps the loop at two follow-up photos per spot.
- Anyone can check the signed result with `python verify.py` from the evidence bundle, without trusting the Twice server.

## 4. The same loop as MCP tools

`server/twice/mcp_server.py` exposes Twice's OpenCV 5 tools over the Model Context Protocol, so any agent can drive a check: Claude Desktop, Claude Code, or `server/eval/mcp_agent.py`. Every tool calls the real API in-process, so the photos, seals, trace and signed report are the same as in the web app.

| Tool | What it does |
|---|---|
| `health` | OpenCV version and build (`COOL` or `pip`), CPU architecture, signer |
| `start_sample_check`, `start_check` | Create a check and seal the move-in photos |
| `check_photo_quality` | Sharpness, exposure and texture of a photo |
| `compare_move_out` | Registration, change map, triage and the next request |
| `submit_followup`, `take_sample_photo` | The side-step or close-up photo the last result asked for |
| `detect_objects` | NanoDet on `cv2.dnn.ENGINE_NEW` |
| `request_human_review` | Hand a finding to a person |
| `seal_report` | Sign the report and verify photos and seals |

Here the agent is a separate process that only sees the tools. It reads each OpenCV result and picks the next call: another photo when a result carries a `request`, a retake on `retake`, human review for `uncertain` and `changed` findings, and the seal when every spot is done. The tools still decide every verdict.

`cd server && python -m eval.mcp_agent` runs Claude as the planner (with `ANTHROPIC_API_KEY`, or `TWICE_BEDROCK_REGION` for Bedrock). `--scripted` runs a fixed policy with the same tools and no model. `--still-camera` is the counterfactual. Traces from the scripted policy:

| Run | Car spot, finding f1 (the chrome reflection) | Agent's next call |
|---|---|---|
| [Renter steps aside](eval/mcp-agent-trace-scripted.md) | `compare_followup`: vanished after the camera moved, rule out as glare | next spot; no review for f1 |
| [Renter does not move](eval/mcp-agent-trace-still-scripted.md) | `parallax_check`: camera moved 0.0% twice, then `budget`: mark cannot judge | `request_human_review(f1)` |

`tests/test_mcp.py` drives both runs through an in-process MCP client and checks that the photo alone changes the agent's call.

To use the tools from Claude Desktop, add this to `claude_desktop_config.json` (use your own paths):

```json
{"mcpServers": {"twice-opencv": {"command": "D:\\opencv\\.venv\\Scripts\\python.exe",
  "args": ["-m", "twice.mcp_server"], "cwd": "D:\\opencv\\server"}}}
```

On a COOL instance, run the same server with COOL's Python: `health` then reports `"opencv_build": "COOL"`, and every tool call runs on COOL.
