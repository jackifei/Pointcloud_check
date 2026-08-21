from __future__ import annotations

import base64
import hashlib
import json
import platform
import sys
import uuid
from datetime import date
from pathlib import Path


class LicenseManager:
    """授权管理器。

    负责：
    - 生成机器码
    - 校验动态密钥
    - 保存激活信息
    - 检查到期时间
    """

    SECRET = "SOP-License-Secret-2026"

    def __init__(self) -> None:
        self.data_path = self._default_data_path()
        self.data = self._load()
        if "machine_code" not in self.data:
            self.data["machine_code"] = self.machine_code()
            self.save()

    @staticmethod
    def machine_code() -> str:
        raw = "|".join(
            [
                platform.system(),
                platform.node(),
                str(uuid.getnode()),
            ]
        )
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
        return "-".join(digest[i : i + 4] for i in range(0, 16, 4))

    @staticmethod
    def _default_data_path() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent / "license_data.json"
        return Path(__file__).resolve().parents[2] / "license_data.json"

    def _load(self) -> dict:
        if not self.data_path.exists():
            return {}
        try:
            data = json.loads(self.data_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def save(self) -> None:
        self.data_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def is_machine_bound(self) -> bool:
        return self.data.get("machine_code") == self.machine_code()

    def is_activated(self) -> bool:
        return bool(self.data.get("activated"))

    def expiry_date(self) -> date | None:
        value = self.data.get("end_date")
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    def is_expired(self) -> bool:
        expiry = self.expiry_date()
        return expiry is not None and date.today() > expiry

    def generate_key(self, machine_code: str, start_date: str, end_date: str) -> str:
        payload = "|".join([machine_code, start_date, end_date])
        signature = hashlib.sha256((self.SECRET + payload).encode("utf-8")).hexdigest()[:16].upper()
        encoded = base64.urlsafe_b64encode(f"{payload}|{signature}".encode("utf-8")).decode("ascii")
        return encoded

    def activate(self, key: str) -> tuple[bool, str]:
        if not self.is_machine_bound():
            return False, "当前电脑未完成机器绑定。"
        try:
            decoded = base64.urlsafe_b64decode(key.encode("ascii")).decode("utf-8")
            payload, signature = decoded.rsplit("|", 1)
            machine_code, start_date, end_date = payload.split("|")
        except Exception:
            return False, "密钥格式错误。"

        expected = hashlib.sha256(
            (self.SECRET + payload).encode("utf-8")
        ).hexdigest()[:16].upper()
        if signature != expected:
            return False, "密钥校验失败。"
        if machine_code != self.machine_code():
            return False, "密钥与当前电脑不匹配。"
        try:
            end = date.fromisoformat(end_date)
            start = date.fromisoformat(start_date)
        except ValueError:
            return False, "授权日期格式错误。"
        if date.today() < start:
            return False, "授权尚未开始。"
        if date.today() > end:
            return False, "授权已过期。"

        self.data.update(
            {
                "activated": True,
                "start_date": start_date,
                "end_date": end_date,
                "key": key,
            }
        )
        self.save()
        return True, f"激活成功，到期日期：{end_date}"
