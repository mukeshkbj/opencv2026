import json
import os
from pathlib import Path

import boto3


class LocalStore:
    def __init__(self, root: str):
        self.root = Path(root)

    def put(self, key: str, data: bytes, content_type: str = "") -> None:
        p = self.root / key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get(self, key: str) -> bytes:
        p = self.root / key
        if not p.is_file():
            raise KeyError(key)
        return p.read_bytes()


class S3Store:
    def __init__(self, bucket: str):
        self.bucket = bucket
        self.s3 = boto3.client("s3")

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type,
                           ServerSideEncryption="aws:kms")

    def get(self, key: str) -> bytes:
        try:
            return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except self.s3.exceptions.NoSuchKey as e:
            raise KeyError(key) from e


def make_store():
    bucket = os.environ.get("TWICE_BUCKET")
    return S3Store(bucket) if bucket else LocalStore(os.environ.get("TWICE_DATA", "data"))


def get_json(store, key: str) -> dict:
    return json.loads(store.get(key))


def put_json(store, key: str, value: dict) -> None:
    store.put(key, json.dumps(value, separators=(",", ":")).encode(), "application/json")
