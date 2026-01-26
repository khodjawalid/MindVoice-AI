import os
from datetime import datetime, timedelta, timezone
import boto3


def get_utc_yesterday() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")


# S3 client factory
def create_s3_client(
    access_key: str,
    secret_key: str,
    region: str,
):
    return boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )


# Core sync function (SERVICE)
def sync_empatica_day(
    *,
    date: str,
    bucket_name: str,
    prefix_root: str,
    device_serial: str,
    local_base_dir: str,
    s3_client,
) -> str:
    """
    Download all Empatica files for a given UTC date.
    Returns the local directory path.
    """

    prefix = (
        f"{prefix_root}1/1/participant_data/"
        f"{date}/{device_serial}/"
    )

    local_dir = os.path.join(local_base_dir, f"empatica_{date}")
    os.makedirs(local_dir, exist_ok=True)

    paginator = s3_client.get_paginator("list_objects_v2")
    downloaded = 0

    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        if "Contents" not in page:
            continue

        for obj in page["Contents"]:
            key = obj["Key"]

            if key.endswith("/"):
                continue

            relative_path = os.path.relpath(key, prefix)
            local_path = os.path.join(local_dir, relative_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Idempotent
            if os.path.exists(local_path):
                continue

            s3_client.download_file(bucket_name, key, local_path)
            downloaded += 1

    print(f"✅ Empatica sync {date}: {downloaded} files")

    return local_dir
