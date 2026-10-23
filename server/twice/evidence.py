"""Canonical manifests signed with AWS KMS (ECDSA P-256) or a local Ed25519 key."""
import base64
import hashlib
import json
import os
from pathlib import Path

import boto3
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class KmsSigner:
    algorithm = "ECDSA_SHA_256"

    def __init__(self, key_id: str):
        self.kms = boto3.client("kms")
        self.key_id = key_id
        self._public = None

    def sign(self, message: bytes) -> str:
        out = self.kms.sign(KeyId=self.key_id, Message=hashlib.sha256(message).digest(),
                            MessageType="DIGEST", SigningAlgorithm=self.algorithm)
        return base64.b64encode(out["Signature"]).decode()

    def public_pem(self) -> str:
        if self._public is None:
            der = self.kms.get_public_key(KeyId=self.key_id)["PublicKey"]
            b64 = base64.encodebytes(der).decode()
            self._public = f"-----BEGIN PUBLIC KEY-----\n{b64}-----END PUBLIC KEY-----\n"
        return self._public


class LocalSigner:
    algorithm = "Ed25519"

    def __init__(self, path: Path):
        if path.exists():
            self.key = serialization.load_pem_private_key(path.read_bytes(), None)
        else:
            self.key = Ed25519PrivateKey.generate()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                    serialization.NoEncryption()))
        self._pem = self.key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()

    def sign(self, message: bytes) -> str:
        return base64.b64encode(self.key.sign(message)).decode()

    def public_pem(self) -> str:
        return self._pem


def make_signer():
    key_id = os.environ.get("TWICE_KMS_KEY_ID")
    if key_id:
        return KmsSigner(key_id)
    return LocalSigner(Path(os.environ.get("TWICE_DATA", "data")) / "signing-key.pem")


def fingerprint(pem: str) -> str:
    key = serialization.load_pem_public_key(pem.encode())
    der = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return "sha256:" + sha256(der)


def verify(pem: str, algorithm: str, message: bytes, signature_b64: str) -> bool:
    key = serialization.load_pem_public_key(pem.encode())
    sig = base64.b64decode(signature_b64)
    try:
        if algorithm == "Ed25519":
            key.verify(sig, message)
        else:
            key.verify(sig, message, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False
