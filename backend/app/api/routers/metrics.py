# app/api/routes/metrics.py
from fastapi import APIRouter
from app.db.supabase import supabase

router = APIRouter(prefix="/metrics", tags=["metrics"])

BATCH_SIZE = 1000


def fetch_all_rows(table: str, select: str, order_by: str):
    """Fetch all rows from a table using pagination (Supabase default limit is 1000)."""
    all_data = []
    offset = 0

    while True:
        res = (
            supabase
            .table(table)
            .select(select)
            .order(order_by, desc=False)
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )

        all_data.extend(res.data)

        if len(res.data) < BATCH_SIZE:
            break

        offset += BATCH_SIZE

    return all_data


@router.get("/")
def get_metrics():
    data = fetch_all_rows(
        table="biometrics_demo",
        select="timestamp_unix, timestamp_iso, eda, heart_rate, has_tag",
        order_by="timestamp_unix"
    )

    return {
        "count": len(data),
        "data": data,
    }
