"""Checks a Twice evidence bundle without the Twice server.

Needs Python 3.10 or later and `pip install cryptography`. Run it in the unzipped bundle:  python verify.py
Compare the printed key fingerprint with the key the issuer publishes; a forger could swap both.
"""
import base64
import hashlib
import json
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def signature_ok(key, seal: dict, body: bytes) -> bool:
    sig = base64.b64decode(seal["signature"])
    try:
        if seal["algorithm"] == "Ed25519":
            key.verify(sig, body)
        else:
            key.verify(sig, body, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False


def photo_hashes(manifest: dict) -> set[str]:
    out = set()
    for s in manifest["spots"]:
        out.add(s["before"]["sha256"])
        if "after" in s:
            out.add(s["after"]["sha256"])
            out.update(f["sha256"] for f in s["followups"])
    return out


def check(root: Path) -> list[str]:
    pem = (root / "public_key.pem").read_bytes()
    key = serialization.load_pem_public_key(pem)
    der = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    print(f"public key fingerprint  sha256:{hashlib.sha256(der).hexdigest()}")
    seals = {s["phase"]: s for s in json.loads((root / "seals.json").read_text(encoding="utf-8"))}
    problems = []
    if "before" not in seals:
        return ["the move-in seal is missing"]
    for phase, seal in seals.items():
        body = canonical(seal["manifest"])
        if hashlib.sha256(body).hexdigest() != seal["digest"]:
            problems.append(f"{phase} seal: the digest does not match the manifest")
        if not signature_ok(key, seal, body):
            problems.append(f"{phase} seal: the signature is not valid")
        print(f"{phase:<7} seal  {seal['digest']}  signed {seal['manifest']['signed_at']}")
    if "report" in seals:
        report = seals["report"]["manifest"]
        if report.get("move_in_seal") != seals["before"]["digest"]:
            problems.append("the report seal does not point to this move-in seal")
        move_in = {s["id"]: s["before"]["sha256"] for s in seals["before"]["manifest"]["spots"]}
        if {s["id"]: s["before"]["sha256"] for s in report["spots"]} != move_in:
            problems.append("the report uses different move-in photos from the move-in seal")
    signed = set().union(*(photo_hashes(s["manifest"]) for s in seals.values()))
    for sha in sorted(signed):
        photo = root / "photos" / f"{sha}.jpg"
        if not photo.exists():
            problems.append(f"photo {sha[:16]} is missing")
        elif hashlib.sha256(photo.read_bytes()).hexdigest() != sha:
            problems.append(f"photo {sha[:16]} was altered")
    print(f"{len(signed)} signed photos checked")
    return problems


if __name__ == "__main__":
    found = check(Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent))
    print("\n".join(["", "NOT VALID:", *found] if found else ["", "VALID: every photo and finding matches its signature."]))
    sys.exit(1 if found else 0)
