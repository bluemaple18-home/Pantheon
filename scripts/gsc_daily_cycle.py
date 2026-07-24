#!/usr/bin/env python3
"""依序執行每日 GSC 成效與 URL inspection 快照。"""

from __future__ import annotations

from scripts import gsc_daily_fetch, gsc_daily_inspection


def main() -> int:
    performance_status = gsc_daily_fetch.main([])
    inspection_status = gsc_daily_inspection.main([])
    return max(performance_status, inspection_status)


if __name__ == "__main__":
    raise SystemExit(main())
