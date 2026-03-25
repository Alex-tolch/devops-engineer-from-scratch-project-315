#!/usr/bin/env python3

from __future__ import annotations

import sys

import boto3
from botocore.config import Config


def _client_config(*, path_style: bool) -> Config:
    kwargs: dict = {"signature_version": "s3v4"}
    if path_style:
        kwargs["s3"] = {"addressing_style": "path"}
    try:
        return Config(
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            **kwargs,
        )
    except TypeError:
        return Config(**kwargs)


def main() -> int:
    if len(sys.argv) != 6:
        print(
            "usage: upload_bulletin_s3_object.py <bucket> <object_key> <file_path> "
            "<endpoint_or_empty> <region>",
            file=sys.stderr,
        )
        return 2

    bucket, object_key, file_path, endpoint_raw, region = sys.argv[1:6]
    endpoint = (endpoint_raw or "").strip() or None

    if endpoint:
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            config=_client_config(path_style=True),
        )
    else:
        client = boto3.client(
            "s3",
            region_name=region,
            config=_client_config(path_style=False),
        )

    with open(file_path, "rb") as fh:
        body = fh.read()

    client.put_object(
        Bucket=bucket,
        Key=object_key,
        Body=body,
        ContentType="image/jpeg",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
