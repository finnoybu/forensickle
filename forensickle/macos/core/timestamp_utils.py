import time
from datetime import datetime, timezone

# Chrome/WebKit epoch: 1601-01-01 in microseconds
_CHROME_EPOCH_DELTA_US = 11644473600 * 1_000_000
# CoreData epoch: 2001-01-01
_COREDATA_EPOCH_DELTA_S = 978307200


def datetime_to_epoch_ms(dt: datetime) -> int | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def chrome_time_to_epoch_ms(chrome_time: int) -> int:
    """Chrome/WebKit timestamp (microseconds since 1601-01-01) to epoch ms."""
    return int((chrome_time - _CHROME_EPOCH_DELTA_US) / 1000)


def firefox_time_to_epoch_ms(firefox_time: int) -> int:
    """Firefox PRTime (microseconds since Unix epoch) to epoch ms."""
    return int(firefox_time / 1000)


def safari_coredata_to_epoch_ms(cd_time: float) -> int:
    """CoreData timestamp (seconds since 2001-01-01) to epoch ms."""
    return int((cd_time + _COREDATA_EPOCH_DELTA_S) * 1000)


def stat_time_to_epoch_ms(stat_time: float) -> int:
    """os.stat timestamp (seconds since Unix epoch) to epoch ms."""
    return int(stat_time * 1000)


def epoch_ms_now() -> int:
    """Current UTC time as epoch ms."""
    return int(time.time() * 1000)
