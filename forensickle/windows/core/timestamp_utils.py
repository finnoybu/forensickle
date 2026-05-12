import time
from datetime import datetime, timezone

# Windows FILETIME epoch: 1601-01-01, offset to Unix epoch in 100ns intervals
_FILETIME_UNIX_DIFF = 116444736000000000

# Chrome/WebKit epoch: 1601-01-01, stored as microseconds
_CHROME_EPOCH_OFFSET = 11644473600000000


def filetime_to_epoch_ms(filetime: int) -> int | None:
    """Windows FILETIME (100ns since 1601-01-01) to Unix epoch milliseconds."""
    if filetime is None or filetime < _FILETIME_UNIX_DIFF:
        return None
    return (filetime - _FILETIME_UNIX_DIFF) // 10000


def datetime_to_epoch_ms(dt: datetime) -> int | None:
    """Datetime to Unix epoch milliseconds. Assumes UTC if naive."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def chrome_time_to_epoch_ms(chrome_time: int) -> int:
    """Chrome/WebKit timestamp (microseconds since 1601-01-01) to epoch ms."""
    return (chrome_time - _CHROME_EPOCH_OFFSET) // 1000


def firefox_time_to_epoch_ms(firefox_time: int) -> int:
    """Firefox PRTime (microseconds since Unix epoch) to epoch ms."""
    return firefox_time // 1000


def epoch_ms_now() -> int:
    """Current UTC time as Unix epoch milliseconds."""
    return int(time.time() * 1000)
