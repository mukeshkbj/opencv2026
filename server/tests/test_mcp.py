"""The MCP tool server, driven in-process by the scripted policy of eval/mcp_agent.py."""
import asyncio
import os
import tempfile

os.environ.setdefault("TWICE_DATA", tempfile.mkdtemp())

from mcp import Client  # noqa: E402

from eval.mcp_agent import scripted  # noqa: E402
from twice import mcp_server  # noqa: E402


def run(still: bool) -> list[dict]:
    os.environ["TWICE_MCP_STILL_CAMERA"] = "1" if still else "0"
    log: list = []

    async def go():
        async with Client(mcp_server.server) as client:
            names = {t.name for t in (await client.list_tools()).tools}
            assert {"compare_move_out", "submit_followup", "seal_report", "request_human_review"} <= names
            await scripted(client, log)

    asyncio.run(go())
    return log


def test_side_step_photo_changes_the_agents_next_call():
    moved, still = run(False), run(True)
    for log in (moved, still):
        assert log[-1]["tool"] == "seal_report" and log[-1]["result"]["verified"] is True
    car = lambda log: [e for e in log if e["args"].get("spot_id") == "s1"]
    # The renter stepped aside: OpenCV rules the mark out as glare, so nobody is asked to review it.
    assert "s1 f1" not in {f"{e['args']['spot_id']} {e['args']['finding_id']}" for e in car(moved)
                           if e["tool"] == "request_human_review"}
    # The renter did not move: OpenCV says the camera moved 0%, the budget runs out, and the agent hands f1 to a person.
    assert any(e["tool"] == "request_human_review" and e["args"]["finding_id"] == "f1" for e in car(still))
