import hashlib
import json
from datetime import datetime
from typing import List


def generate_session_hash(
    session_id: str,
    participant_ids: List[str],
    video_checksums: List[str],
    confirmation_timestamps: List[str],
    sealed_at: str,
) -> str:
    """Generate a tamper-evident hash for a sealed session"""
    payload = {
        "session_id": session_id,
        "participant_ids": sorted(participant_ids),
        "video_checksums": sorted(video_checksums),
        "confirmation_timestamps": sorted(confirmation_timestamps),
        "sealed_at": sealed_at,
    }
    payload_str = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(payload_str.encode()).hexdigest()


def verify_session_hash(session_hash: str, payload: dict) -> bool:
    """Verify a session hash hasn't been tampered with"""
    payload_str = json.dumps(payload, sort_keys=True)
    computed = hashlib.sha256(payload_str.encode()).hexdigest()
    return computed == session_hash


def compute_file_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
