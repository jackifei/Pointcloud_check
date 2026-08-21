from __future__ import annotations

import csv
import sys
from datetime import date, datetime
from pathlib import Path


class LogService:
    """日志文件服务。

    按天写入项目根目录下的 log/YYYYMMDD.txt，使用逗号分隔格式，
    便于直接当作 CSV 打开查看。
    """

    HEADER = ("时间", "级别", "来源", "消息")

    def __init__(self, root_dir: Path | None = None) -> None:
        if root_dir is not None:
            self.root_dir = root_dir
        elif getattr(sys, "frozen", False):
            self.root_dir = Path(sys.executable).resolve().parent
        else:
            self.root_dir = Path(__file__).resolve().parents[2]
        self.log_dir = self.root_dir / "log"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def today_file(self) -> Path:
        return self.log_dir / f"{date.today():%Y%m%d}.txt"

    def append(self, level: str, source: str, message: str) -> None:
        path = self.today_file()
        is_new = not path.exists()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with path.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow(self.HEADER)
            writer.writerow([now, level, source, message])

    def load_today(self, limit: int = 100) -> list[tuple[str, str, str, str]]:
        path = self.today_file()
        if not path.exists():
            return []
        rows: list[tuple[str, str, str, str]] = []
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                if row[0] == self.HEADER[0] and row[1:] == list(self.HEADER[1:]):
                    continue
                time_text = row[0] if len(row) > 0 else ""
                level = row[1] if len(row) > 1 else ""
                source = row[2] if len(row) > 2 else ""
                message = row[3] if len(row) > 3 else ""
                rows.append((time_text, level, source, message))
        return rows[-limit:]

    def clear_today(self) -> None:
        path = self.today_file()
        if path.exists():
            path.unlink()
