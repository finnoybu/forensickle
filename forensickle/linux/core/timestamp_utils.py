import time
from datetime import datetime, timezone


def datetime_to_epoch_ms(dt: datetime) -> int | None:
    """Convert datetime to Unix epoch milliseconds. Returns None for None input."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def stat_time_to_epoch_ms(stat_time: float) -> int:
    """Convert os.stat timestamp (seconds float) to epoch ms."""
    return int(stat_time * 1000)


def normalize_timestamp_ms(ts: int | float) -> int:
    """Normalize seconds/ms/us/ns to milliseconds based on digit count."""
    ts = int(ts)
    digits = len(str(abs(ts)))
    if digits <= 10:      # seconds
        return ts * 1000
    elif digits <= 13:    # milliseconds
        return ts
    elif digits <= 16:    # microseconds
        return ts // 1000
    else:                 # nanoseconds
        return ts // 1_000_000


_CHROME_EPOCH_OFFSET = 11644473600000000


def chrome_time_to_epoch_ms(chrome_time: int) -> int:
    """Chrome/WebKit timestamp (microseconds since 1601-01-01) to epoch ms."""
    return (chrome_time - _CHROME_EPOCH_OFFSET) // 1000


def firefox_time_to_epoch_ms(firefox_time: int) -> int:
    """Firefox PRTime (microseconds since Unix epoch) to epoch ms."""
    return firefox_time // 1000


def epoch_ms_now() -> int:
    """Current UTC time as epoch milliseconds."""
    return int(time.time() * 1000)
