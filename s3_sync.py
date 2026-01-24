from dotenv import load_dotenv
import os
import boto3
from datetime import datetime, timedelta, timezone

# -----------------------------------------------------------------------------
# Environment
# -----------------------------------------------------------------------------
load_dotenv()

S3_BUCKET = os.getenv("EMPATICA_S3_BUCKET")
S3_REGION = os.getenv("EMPATICA_S3_REGION", "us-east-1")
S3_PREFIX = os.getenv("EMPATICA_S3_PREFIX")  # e.g. "v2/2580/"
USER_DEVICE = os.getenv("EMPATICA_DEVICE_SERIAL", "28-3YK651D16C")

BASE_LOCAL_DIR = "./empatica_data"

# AWS Client
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("EMPATICA_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("EMPATICA_SECRET_ACCESS_KEY"),
    region_name=S3_REGION,
)

# Date logic
def get_utc_yesterday() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

# S3 Sync
def s3_sync(bucket_name: str, prefix: str, local_dir: str) -> None:
    os.makedirs(local_dir, exist_ok=True)
    paginator = s3.get_paginator("list_objects_v2")

    downloaded = 0

    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        if "Contents" not in page:
            continue

        for obj in page["Contents"]:
            key = obj["Key"]

            # Skip folders
            if key.endswith("/"):
                continue

            relative_path = os.path.relpath(key, prefix)
            local_path = os.path.join(local_dir, relative_path)

            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Idempotent: skip if already downloaded
            if os.path.exists(local_path):
                continue

            print(f"⬇️  Downloading {key}")
            s3.download_file(bucket_name, key, local_path)
            downloaded += 1

    print(f"✅ S3 sync complete — {downloaded} files downloaded")


if __name__ == "__main__":
    date = get_utc_yesterday()

    prefix = (
        f"{S3_PREFIX}1/1/participant_data/"
        f"{date}/{USER_DEVICE}/"
    )

    local_dir = f"{BASE_LOCAL_DIR}/empatica_{date}"

    print(f"📅 Syncing date: {date}")
    print(f"📂 S3 prefix: {prefix}")

    s3_sync(S3_BUCKET, prefix, local_dir)
