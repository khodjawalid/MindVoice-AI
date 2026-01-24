from dotenv import load_dotenv
import os
import boto3

load_dotenv()

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("EMPATICA_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("EMPATICA_SECRET_ACCESS_KEY"),
    region_name=os.getenv("EMPATICA_S3_REGION", "us-east-1"),
)

bucket_name = os.getenv("EMPATICA_S3_BUCKET")
date = "2026-01-16" ## Fix 
user_device = "28-3YK651D16C"
prefix = f"{os.getenv('EMPATICA_S3_PREFIX')}1/1/participant_data/{date}/{user_device}/"
local_dir = f"./empatica_{date}"

def s3_sync(bucket_name: str, prefix: str, local_dir: str) -> None:
    os.makedirs(local_dir, exist_ok=True)
    paginator = s3.get_paginator("list_objects_v2")
    
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
            
            if os.path.exists(local_path):
                continue
                
            print(f"Downloading {key}")
            s3.download_file(bucket_name, key, local_path)
    
    print("S3 sync complete")


if __name__ == "__main__":
    s3_sync(bucket_name, prefix, local_dir)