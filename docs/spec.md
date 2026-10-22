# Twice — spec

**Pitch.** Take the same photo twice. Twice shows what really changed, and it signs the proof.

**Hook.** Hertz's AI scanners billed a renter $440 for a one-inch wheel scuff, with no human review. Rental companies have AI. Renters do not.

## Decision record
- Persona panel (7 personas) ranked this idea first over pill check, wound tracker, and appliance troubleshooter. Full critique: `docs/critique-round1.md`.
- Name changed from "Alibi" to "Twice". "Alibi" implies guilt. A non-technical parent understood "take the same photo again and it shows what changed" at once.
- Crowded lane to avoid: generic "agent inspects a part and escalates". Twice is consumer-facing and the guided re-capture is the differentiator.

## User flow
1. **Before.** The user photographs 3 to 6 spots. A live quality gate (sharpness, light, detail) enables the shutter. Each photo is hashed and timestamped.
2. **Seal.** The before set gets a signed manifest. A share link lets the other party see the set.
3. **After.** For each spot, a ghost of the before photo locks onto the live view. Directions ("pan left", "move closer") guide the user back to the same pose. The app captures automatically when the pose matches and the frame is sharp.
4. **Analysis.** The agent registers the pair, builds a change map, and resolves each candidate region. It can ask for a follow-up photo: a parallax shot (glare moves when the camera moves, damage does not) or a close-up.
5. **Report.** Each spot gets a before/after wipe with callouts in three classes: changed, lighting only, cannot judge. The manifest is signed. A verify page re-hashes the files.

## Agent loop
Goal: every candidate region ends in a class with evidence.
Tools: `register`, `change_map`, `relight_check`, `glare_check`, `request_parallax`, `request_closeup`, `compare_followup`, `caption`.
- The planner picks the next tool from the evidence table. A rule planner runs locally. With Bedrock credentials, Claude plans through the Converse tool-use API.
- Guard rails: the language model can label and escalate. It cannot delete a region. Follow-up requests are capped at 2 per spot. Text inside images is data, not instructions.

## Non-goals (cut for scope)
Video input, room coverage maps, 3D reconstruction, accounts.
