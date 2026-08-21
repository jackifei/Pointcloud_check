from __future__ import annotations

import csv
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

from .config_service import ConfigService


class ProductionCounterService:
    """生产计数服务。

    负责 OK/NG、日/周/月计数的持久化，并在启动时根据日期或班次
    判断是否需要清零；清零前的数值会写入 checknum/check_result_num.txt。
    """

    STATE_FILENAME = "counter_state.json"
    RESULT_FILENAME = "check_result_num.txt"
    RESULT_HEADER = ("日期", "统计项", "清零前数值")

    def __init__(self, root_dir: Path | None = None) -> None:
        self.config_service = ConfigService(root_dir)
        self.root_dir = self.config_service.root_dir
        self.checknum_dir = self.root_dir / "checknum"
        self.checknum_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.checknum_dir / self.STATE_FILENAME
        self.result_path = self.checknum_dir / self.RESULT_FILENAME
        self.state = self._load_state()
        self._check_resets(datetime.now())
        self._save_state()

    def _load_state(self) -> dict:
        today = date.today()
        defaults = {
            "ok": 0,
            "ng": 0,
            "day": 0,
            "week": 0,
            "month": 0,
            "last_ok_reset": today.isoformat(),
            "last_day_reset": today.isoformat(),
            "last_week_reset": self._week_start(today).isoformat(),
            "last_month_reset": today.replace(day=1).isoformat(),
        }
        if not self.state_path.exists():
            return defaults
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                defaults.update(data)
        except (OSError, json.JSONDecodeError):
            pass
        return defaults

    def _save_state(self) -> None:
        self.state_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _system_config(self) -> dict:
        return self.config_service.load_page_config("system")

    def _check_resets(self, now: datetime) -> None:
        system = self._system_config()
        counting_mode = system.get("counting_mode", "day")
        shifts = system.get("shifts", [])

        self._check_day(now.date())
        self._check_week(now.date())
        self._check_month(now.date())
        self._check_ok_ng(now, counting_mode, shifts)

    def _check_day(self, today: date) -> None:
        last = self._parse_date(self.state.get("last_day_reset"))
        if last != today:
            self._record_reset(today, "日", self.state.get("day", 0))
            self.state["day"] = 0
            self.state["last_day_reset"] = today.isoformat()

    def _check_week(self, today: date) -> None:
        week_start = self._week_start(today)
        last = self._parse_date(self.state.get("last_week_reset"))
        if last != week_start:
            self._record_reset(today, "周", self.state.get("week", 0))
            self.state["week"] = 0
            self.state["last_week_reset"] = week_start.isoformat()

    def _check_month(self, today: date) -> None:
        month_start = today.replace(day=1)
        last = self._parse_date(self.state.get("last_month_reset"))
        if last != month_start:
            self._record_reset(today, "月", self.state.get("month", 0))
            self.state["month"] = 0
            self.state["last_month_reset"] = month_start.isoformat()

    def _check_ok_ng(self, now: datetime, mode: str, shifts: list[dict]) -> None:
        if mode == "shift":
            latest_start = self._latest_shift_start(shifts, now)
            if latest_start is not None:
                last = self._parse_datetime(self.state.get("last_ok_reset"))
                if last is None or last < latest_start:
                    self._reset_ok_ng(now.date(), latest_start.strftime("%Y-%m-%d %H:%M:%S"))
                return

        today = now.date()
        last = self._parse_date(self.state.get("last_ok_reset"))
        if last != today:
            self._reset_ok_ng(today, today.isoformat())

    def _reset_ok_ng(self, today: date, last_reset_value: str) -> None:
        self._record_reset(today, "OK", self.state.get("ok", 0))
        self._record_reset(today, "NG", self.state.get("ng", 0))
        self.state["ok"] = 0
        self.state["ng"] = 0
        self.state["last_ok_reset"] = last_reset_value

    def _record_reset(self, day: date, kind: str, value: int) -> None:
        value = int(value or 0)
        if not self.result_path.exists():
            with self.result_path.open("a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(self.RESULT_HEADER)
        with self.result_path.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([day.isoformat(), kind, value])

    def snapshot(self) -> dict:
        ok = int(self.state.get("ok", 0))
        ng = int(self.state.get("ng", 0))
        total = ok + ng
        ok_rate = round(ok / total * 100, 1) if total > 0 else 0.0
        return {
            "ok": ok,
            "ng": ng,
            "day": int(self.state.get("day", 0)),
            "week": int(self.state.get("week", 0)),
            "month": int(self.state.get("month", 0)),
            "ok_rate": ok_rate,
        }

    def add_result(self, is_ok: bool) -> None:
        """新增一次检测结果，供后续真实检测流程调用。"""
        if is_ok:
            self.state["ok"] = int(self.state.get("ok", 0)) + 1
        else:
            self.state["ng"] = int(self.state.get("ng", 0)) + 1
        self.state["day"] = int(self.state.get("day", 0)) + 1
        self.state["week"] = int(self.state.get("week", 0)) + 1
        self.state["month"] = int(self.state.get("month", 0)) + 1
        self._save_state()

    @staticmethod
    def _week_start(day: date) -> date:
        return day - timedelta(days=day.weekday())

    @staticmethod
    def _parse_date(value) -> date | None:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        text = str(value or "")
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None

    @staticmethod
    def _parse_datetime(value) -> datetime | None:
        text = str(value or "")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            try:
                return datetime.combine(date.fromisoformat(text), time.min)
            except ValueError:
                return None

    @staticmethod
    def _parse_time(value) -> time | None:
        text = str(value or "")
        try:
            return time.fromisoformat(text)
        except ValueError:
            return None

    def _latest_shift_start(self, shifts: list[dict], now: datetime) -> datetime | None:
        candidates: list[datetime] = []
        today = now.date()
        for shift in shifts or []:
            start = self._parse_time(shift.get("start"))
            end = self._parse_time(shift.get("end"))
            if start is None or end is None or start == end:
                continue
            candidates.append(datetime.combine(today, start))
            candidates.append(datetime.combine(today - timedelta(days=1), start))
        candidates = [candidate for candidate in candidates if candidate <= now]
        return max(candidates) if candidates else None
