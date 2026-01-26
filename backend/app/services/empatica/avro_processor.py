"""
Empatica AVRO Processor Service

Processes AVRO files from synced Empatica data and extracts:
- EDA (electrodermal activity) raw and per-minute
- HR (heart rate) raw and per-minute
- Tags (user-marked events)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

import pandas as pd
from fastavro import reader


@dataclass
class EmpaticaPaths:
    """Paths configuration for AVRO processing."""
    avro_dir: Path
    out_dir: Path
    date: str


class EmpaticaAvroProcessor:
    """
    Processes Empatica AVRO files to extract physiological signals.

    Input: {local_dir}/v6/*.avro
    Output: {local_dir}/processed_raw/*.csv
    """

    def __init__(self, paths: EmpaticaPaths):
        self.paths = paths
        self.eda_records: List[Dict] = []
        self.hr_records: List[Dict] = []
        self.tag_records: List[Dict] = []

    def process_day(self) -> Dict[str, Path]:
        """
        Process all AVRO files for the day.

        Returns dict mapping output type to file path.
        """
        self.paths.out_dir.mkdir(parents=True, exist_ok=True)

        # Process all AVRO files
        avro_files = list(self.paths.avro_dir.glob("*.avro"))
        for avro_file in avro_files:
            self._process_avro_file(avro_file)

        # Generate output CSVs
        outputs = {}

        if self.eda_records:
            outputs["eda_raw"] = self._save_eda_raw()
            outputs["eda_per_minute"] = self._save_eda_per_minute()

        if self.hr_records:
            outputs["hr_raw"] = self._save_hr_raw()
            outputs["hr_per_minute"] = self._save_hr_per_minute()

        if self.tag_records:
            outputs["tags_raw"] = self._save_tags()

        return outputs

    def _process_avro_file(self, avro_file: Path) -> None:
        """Extract data from a single AVRO file."""
        with open(avro_file, "rb") as f:
            for record in reader(f):
                self._extract_eda(record)
                self._extract_hr(record)
                self._extract_tags(record)

    def _extract_eda(self, record: Dict) -> None:
        """Extract EDA (electrodermal activity) data from record."""
        if "rawData" not in record:
            return
        raw_data = record["rawData"]
        if "eda" not in raw_data:
            return

        eda_data = raw_data["eda"]
        if not eda_data:
            return

        # Get timestamp and sampling frequency
        timestamp_start = eda_data.get("timestampStart", 0) / 1_000_000  # micros to seconds
        sampling_freq = eda_data.get("samplingFrequency", 4.0)
        values = eda_data.get("values", [])

        for i, value in enumerate(values):
            ts = timestamp_start + (i / sampling_freq)
            self.eda_records.append({
                "timestamp": ts,
                "datetime_utc": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                "eda_us": value,  # microsiemens
            })

    def _extract_hr(self, record: Dict) -> None:
        """Extract heart rate data from record."""
        if "rawData" not in record:
            return
        raw_data = record["rawData"]

        # Use IBI (inter-beat interval) from systolicPeaks to compute HR
        # Note: BVP data could also derive HR through peak detection,
        # but systolicPeaks provides more reliable timing
        if "systolicPeaks" in raw_data and raw_data["systolicPeaks"]:
            sp = raw_data["systolicPeaks"]
            peaks_time = sp.get("peaksTimeNanos", [])

            if len(peaks_time) >= 2:
                for i in range(1, len(peaks_time)):
                    ts = peaks_time[i] / 1_000_000_000
                    ibi_ns = peaks_time[i] - peaks_time[i-1]
                    ibi_ms = ibi_ns / 1_000_000
                    if ibi_ms > 0:
                        hr = 60000 / ibi_ms  # Convert IBI to BPM
                        if 30 < hr < 220:  # Sanity check
                            self.hr_records.append({
                                "timestamp": ts,
                                "datetime_utc": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                                "hr_bpm": round(hr, 1),
                                "ibi_ms": round(ibi_ms, 1),
                            })

    def _extract_tags(self, record: Dict) -> None:
        """Extract user-tagged events from record."""
        if "rawData" not in record:
            return
        raw_data = record["rawData"]

        if "tags" not in raw_data:
            return

        tags_data = raw_data["tags"]
        if not tags_data:
            return

        tags_time = tags_data.get("tagsTimeMicros", [])
        for tag_time in tags_time:
            ts = tag_time / 1_000_000  # micros to seconds
            self.tag_records.append({
                "timestamp": ts,
                "datetime_utc": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            })

    def _save_eda_raw(self) -> Path:
        """Save raw EDA data to CSV."""
        df = pd.DataFrame(self.eda_records)
        df = df.sort_values("timestamp").reset_index(drop=True)

        out_path = self.paths.out_dir / f"eda_raw_{self.paths.date}.csv"
        df.to_csv(out_path, index=False)
        return out_path

    def _save_eda_per_minute(self) -> Path:
        """Save EDA aggregated per minute."""
        df = pd.DataFrame(self.eda_records)
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        df = df.set_index("datetime")

        # Resample to 1-minute intervals
        df_minute = df["eda_us"].resample("1min").agg(["mean", "std", "min", "max", "count"])
        df_minute = df_minute.reset_index()
        df_minute.columns = ["datetime_utc", "eda_mean", "eda_std", "eda_min", "eda_max", "sample_count"]

        out_path = self.paths.out_dir / f"eda_per_minute_{self.paths.date}.csv"
        df_minute.to_csv(out_path, index=False)
        return out_path

    def _save_hr_raw(self) -> Path:
        """Save raw HR data to CSV."""
        df = pd.DataFrame(self.hr_records)
        df = df.sort_values("timestamp").reset_index(drop=True)

        out_path = self.paths.out_dir / f"hr_raw_{self.paths.date}.csv"
        df.to_csv(out_path, index=False)
        return out_path

    def _save_hr_per_minute(self) -> Path:
        """Save HR aggregated per minute."""
        df = pd.DataFrame(self.hr_records)
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        df = df.set_index("datetime")

        # Resample to 1-minute intervals
        df_minute = df["hr_bpm"].resample("1min").agg(["mean", "std", "min", "max", "count"])
        df_minute = df_minute.reset_index()
        df_minute.columns = ["datetime_utc", "hr_mean", "hr_std", "hr_min", "hr_max", "sample_count"]

        out_path = self.paths.out_dir / f"hr_per_minute_{self.paths.date}.csv"
        df_minute.to_csv(out_path, index=False)
        return out_path

    def _save_tags(self) -> Path:
        """Save tags data to CSV."""
        df = pd.DataFrame(self.tag_records)
        df = df.sort_values("timestamp").reset_index(drop=True)

        out_path = self.paths.out_dir / f"tags_raw_{self.paths.date}.csv"
        df.to_csv(out_path, index=False)
        return out_path


def find_avro_files(local_path: Path) -> Tuple[Optional[Path], List[Path]]:
    """
    Find AVRO files in the local directory.

    Searches in order:
    1. {local_dir}/raw_data/v6/*.avro (S3 sync structure)
    2. {local_dir}/v6/*.avro (alternative)
    3. {local_dir}/**/*.avro (recursive fallback)

    Returns (avro_dir, avro_files) or (None, []) if not found.
    """
    # Try raw_data/v6 first (matches S3 sync structure)
    avro_dir = local_path / "raw_data" / "v6"
    if avro_dir.exists():
        avro_files = list(avro_dir.glob("*.avro"))
        if avro_files:
            return avro_dir, avro_files

    # Try v6 directly
    avro_dir = local_path / "v6"
    if avro_dir.exists():
        avro_files = list(avro_dir.glob("*.avro"))
        if avro_files:
            return avro_dir, avro_files

    # Fallback: search recursively
    avro_files = list(local_path.glob("**/*.avro"))
    if avro_files:
        # Use parent of first file as avro_dir
        return avro_files[0].parent, avro_files

    return None, []


def process_empatica_avro(
    *,
    local_dir: str,
    date: str,
) -> dict:
    """
    Process AVRO files from synced Empatica data.

    Input:  {local_dir}/raw_data/v6/*.avro (or other locations)
    Output: {local_dir}/processed_raw/*.csv

    Returns: {
        "status": "success|skipped|error",
        "output_dir": str,
        "files": {"eda_raw": path, "hr_raw": path, ...}
    }
    """
    local_path = Path(local_dir)
    out_dir = local_path / "processed_raw"

    # Find AVRO files
    avro_dir, avro_files = find_avro_files(local_path)

    if not avro_files:
        return {
            "status": "skipped",
            "reason": "no_avro_files",
            "message": f"No AVRO files found in {local_path}",
            "searched": [
                str(local_path / "raw_data" / "v6"),
                str(local_path / "v6"),
                f"{local_path}/**/*.avro",
            ],
        }

    # Idempotent check - skip if already processed
    if out_dir.exists() and any(out_dir.glob("*.csv")):
        return {
            "status": "skipped",
            "reason": "already_processed",
            "output_dir": str(out_dir),
        }

    # Process AVRO files (avro_dir is guaranteed non-None if avro_files is not empty)
    assert avro_dir is not None
    paths = EmpaticaPaths(avro_dir=avro_dir, out_dir=out_dir, date=date)
    processor = EmpaticaAvroProcessor(paths)

    try:
        outputs = processor.process_day()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }

    return {
        "status": "success",
        "output_dir": str(out_dir),
        "files": {k: str(v) for k, v in outputs.items()},
        "avro_files_processed": len(avro_files),
    }
