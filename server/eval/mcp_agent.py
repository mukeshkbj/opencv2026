"""An agent that runs a Twice move-out check through the MCP tool server (twice/mcp_server.py).

Run from server/:
    python -m eval.mcp_agent                  # Claude plans the tool calls (needs a key, see below)
    python -m eval.mcp_agent --scripted       # a fixed policy, no model, same tools
    python -m eval.mcp_agent --still-camera   # counterfactual: the renter does not move for side-step photos

Claude runs on the Anthropic API when ANTHROPIC_API_KEY is set, or on Amazon Bedrock when TWICE_BEDROCK_REGION is
set (model TWICE_AGENT_MODEL). The server is a separate process on stdio, so the agent sees only the MCP tools.
Writes docs/eval/mcp-agent-trace.json and .md (with a -still suffix for the counterfactual).
"""
import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from mcp import Client, StdioServerParameters

SERVER_DIR = Path(__file__).resolve().parents[1]
OUT = SERVER_DIR.parent / "docs" / "eval"
MAX_TURNS = 40

SYSTEM = (
    "You are the inspection agent of Twice, a move-out check for renters. Use the MCP tools to finish the bundled "
    "sample check: start it, then take the move-out photo of every spot with take_sample_photo. Read each result. "
    "If it has a `request`, call take_sample_photo again for that spot to get exactly that photo; if the status is "
    "'retake', take the photo again. When a spot is done, call request_human_review for each finding whose verdict "
    "is 'uncertain' (say why a person must judge it) and for each 'changed' finding (so a person confirms the claim). "
    "When every spot is done, call seal_report. Before each tool call, write one short sentence that names the "
    "measurement or status that made you choose it. The tools decide verdicts; never state a verdict a tool did not "
    "return. Finish with a three-line summary for the renter."
)


def summary(result: dict | list) -> dict:
    """The parts of a tool result that explain the next decision."""
    if not isinstance(result, dict):
        return {"items": result}
    out = {k: result[k] for k in ("status", "request", "sealed", "verified", "human_reviews", "queued",
                                  "opencv", "opencv_build", "machine") if k in result}
    if "findings" in result:
        out["findings"] = [f"{f['id']} {f['verdict']} ({f['kind']})" for f in result["findings"]]
    if "new_trace" in result:
        out["opencv_trace"] = [f"{t['tool']}: {t['result']}" + (f" -> {t['decision']}" if t["decision"] else "")
                               for t in result["new_trace"]]
    if "spots" in result:
        out["spots"] = [s["spot_id"] for s in result["spots"]]
    return out


async def call(client: Client, name: str, args: dict) -> tuple[dict | list, bool]:
    res = await client.call_tool(name, args)
    if res.is_error:
        return {"error": " ".join(getattr(c, "text", "") for c in res.content)}, True
    data = res.structured_content
    if isinstance(data, dict) and set(data) == {"result"}:
        data = data["result"]
    if data is None:
        data = json.loads(res.content[0].text)
    return data, False


async def scripted(client: Client, log: list) -> str:
    """Follows the server's instructions without a model, so the run works with no key and is repeatable."""
    async def step(reason: str, name: str, args: dict):
        data, err = await call(client, name, args)
        log.append({"actor": "scripted", "reason": reason, "tool": name, "args": args, "result": summary(data),
                    "error": err})
        return data

    await step("Record which OpenCV build runs the tools.", "health", {})
    check = await step("Start the sample check.", "start_sample_check", {})
    cid = check["check_id"]
    for s in check["spots"]:
        spot = await step(f"{s['label']}: no move-out photo yet.", "take_sample_photo", {"check_id": cid, "spot_id": s["spot_id"]})
        for _ in range(4):
            if spot["status"] == "done":
                break
            why = (f"OpenCV asked for a {spot['request']['kind']} photo of {spot['request']['finding']}"
                   if spot["request"] else f"status is {spot['status']}")
            spot = await step(why + ".", "take_sample_photo", {"check_id": cid, "spot_id": s["spot_id"]})
        for f in spot["findings"]:
            if f["verdict"] in ("uncertain", "changed"):
                reason = ("The tools could not judge it" if f["verdict"] == "uncertain"
                          else "A person must confirm a damage claim") + f": {f['evidence'][-1]}"
                await step(f"{f['id']} is {f['verdict']}.", "request_human_review",
                           {"check_id": cid, "spot_id": s["spot_id"], "finding_id": f["id"], "reason": reason})
    report = await step("Every spot is done.", "seal_report", {"check_id": cid})
    return f"Sealed: {report.get('verified')}. Findings: {', '.join(summary(report).get('findings', []))}."


def make_model():
    if os.environ.get("ANTHROPIC_API_KEY"):
        from anthropic import Anthropic
        return Anthropic(), os.environ.get("TWICE_AGENT_MODEL", "claude-opus-5-5")
    if os.environ.get("TWICE_BEDROCK_REGION"):
        from anthropic import AnthropicBedrockMantle
        return (AnthropicBedrockMantle(aws_region=os.environ["TWICE_BEDROCK_REGION"]),
                os.environ.get("TWICE_AGENT_MODEL", "anthropic.claude-opus-5-5"))
    sys.exit("Set ANTHROPIC_API_KEY or TWICE_BEDROCK_REGION, or run with --scripted.")


async def with_claude(client: Client, log: list) -> str:
    model, model_id = make_model()
    listed = await client.list_tools()
    tools = [{"name": t.name, "description": t.description or "",
              "input_schema": getattr(t, "input_schema", None) or getattr(t, "inputSchema")} for t in listed.tools]
    messages = [{"role": "user", "content": "Run the sample move-out check end to end."}]
    for _ in range(MAX_TURNS):
        msg = model.messages.create(model=model_id, max_tokens=2000, system=SYSTEM, tools=tools, messages=messages)
        messages.append({"role": "assistant", "content": [b.model_dump(exclude_none=True) for b in msg.content]})
        text = " ".join(b.text for b in msg.content if b.type == "text").strip()
        uses = [b for b in msg.content if b.type == "tool_use"]
        if not uses:
            return text
        results = []
        for i, b in enumerate(uses):
            data, err = await call(client, b.name, b.input)
            log.append({"actor": model_id, "reason": text if i == 0 else "", "tool": b.name, "args": b.input,
                        "result": summary(data), "error": err})
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(data), "is_error": err})
        messages.append({"role": "user", "content": results})
    return "Stopped: turn limit reached."


def markdown(log: list, final: str, mode: str, still: bool) -> str:
    lines = ["# Agent run over MCP", "",
             f"Generated by `cd server && python -m eval.mcp_agent{' --scripted' if mode == 'scripted' else ''}"
             f"{' --still-camera' if still else ''}`. Planner: **{mode}**. The agent talks to `twice/mcp_server.py` over "
             "stdio and sees only its tools. **OpenCV trace** is what the OpenCV 5 tools measured and decided inside "
             "that call; **Why** is the agent's stated reason for the call.", ""]
    if still:
        lines += ["Counterfactual: the camera returns the move-out photo again for every side-step request.", ""]
    lines += ["| # | Why | Tool call | Result | OpenCV trace |", "|---|---|---|---|---|"]
    for i, e in enumerate(log, 1):
        r = dict(e["result"])
        trace = "<br>".join(r.pop("opencv_trace", []))
        args = ", ".join(f"{k}={v}" for k, v in e["args"].items())
        cell = "; ".join(f"{k}: {json.dumps(v) if not isinstance(v, str) else v}" for k, v in r.items())
        lines.append(f"| {i} | {e['reason'].replace('|', '/').replace(chr(10), ' ')} | `{e['tool']}({args})` | "
                     f"{cell.replace('|', '/')} | {trace.replace('|', '/')} |")
    return "\n".join(lines + ["", "## Final message", "", final, ""])


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scripted", action="store_true")
    ap.add_argument("--still-camera", action="store_true")
    a = ap.parse_args()
    env = {"TWICE_DATA": os.environ.get("TWICE_DATA", tempfile.mkdtemp()), "PYTHONUTF8": "1"}
    if a.still_camera:
        env["TWICE_MCP_STILL_CAMERA"] = "1"
    params = StdioServerParameters(command=sys.executable, args=["-m", "twice.mcp_server"], cwd=str(SERVER_DIR), env=env)
    log: list = []
    async with Client(params) as client:
        final = await (scripted(client, log) if a.scripted else with_claude(client, log))
    mode = "scripted" if a.scripted else os.environ.get("TWICE_AGENT_MODEL", "claude")
    name = "mcp-agent-trace" + ("-still" if a.still_camera else "") + ("-scripted" if a.scripted else "")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps({"planner": mode, "still_camera": a.still_camera, "steps": log,
                                                  "final": final}, indent=1), encoding="utf-8")
    (OUT / f"{name}.md").write_text(markdown(log, final, mode, a.still_camera), encoding="utf-8")
    print(f"{len(log)} tool calls. Wrote docs/eval/{name}.md\n{final}")


if __name__ == "__main__":
    asyncio.run(main())
