from __future__ import annotations

import sys
import shutil
from pathlib import Path
from typing import Any

import yaml


class ConfigService:
    """统一配置读写服务。

    页面配置保存到 config/<页面名>.yaml；
    流程模板保存到 flow/<模板名>/template.yaml。

    插入点：后续如需远程配置中心，可在此替换读写后端。
    """

    TEMPLATE_SUBDIRS = ("ROI Config", "Detection Config", "Model Config", "Other Config")
    LEGACY_TEMPLATE_SUBDIRS = ("ROI配置", "检测参数配置", "模型配置", "其他配置")

    def __init__(self, root_dir: Path | None = None) -> None:
        if root_dir is not None:
            self.root_dir = root_dir
        elif getattr(sys, "frozen", False):
            # PyInstaller 打包后，配置和流程目录放在 exe 同级目录，保证可读可写。
            self.root_dir = Path(sys.executable).resolve().parent
        else:
            self.root_dir = Path(__file__).resolve().parents[2]
        self.config_dir = self.root_dir / "config"
        self.flow_dir = self.root_dir / "flow"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.flow_dir.mkdir(parents=True, exist_ok=True)
        self._copy_bundled_runtime_data()

    def _copy_bundled_runtime_data(self) -> None:
        """PyInstaller 打包后，把 exe 内自带的 config/flow 初始文件复制到 exe 同级目录。"""
        bundle_root = getattr(sys, "_MEIPASS", None)
        if not bundle_root:
            return
        bundle_root = Path(bundle_root)
        for folder_name in ("config", "flow"):
            source = bundle_root / folder_name
            target = self.root_dir / folder_name
            if not source.exists():
                continue
            target.mkdir(parents=True, exist_ok=True)
            for child in source.rglob("*"):
                relative = child.relative_to(source)
                destination = target / relative
                if child.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                elif not destination.exists():
                    shutil.copy2(child, destination)

    def page_config_path(self, page_name: str) -> Path:
        return self.config_dir / f"{page_name}.yaml"

    def template_dir(self, template_name: str) -> Path:
        directory = self.flow_dir / template_name
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def list_templates(self) -> list[str]:
        """列出 flow 目录下所有模板目录名（隐藏目录除外）。"""
        if not self.flow_dir.exists():
            return []
        names: list[str] = []
        for child in self.flow_dir.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                names.append(child.name)
        return sorted(names)

    def ensure_template_dirs(self, template_name: str) -> list[Path]:
        """确保模板目录下存在四个英文配置子目录，并迁移旧中文子目录。"""
        base = self.template_dir(template_name)
        paths: list[Path] = []
        for english, legacy in zip(self.TEMPLATE_SUBDIRS, self.LEGACY_TEMPLATE_SUBDIRS):
            english_dir = base / english
            legacy_dir = base / legacy

            if legacy_dir.exists() and not english_dir.exists():
                legacy_dir.rename(english_dir)

            english_dir.mkdir(parents=True, exist_ok=True)
            if legacy_dir.exists():
                for child in legacy_dir.iterdir():
                    target = english_dir / child.name
                    if child.is_dir():
                        shutil.copytree(child, target, dirs_exist_ok=True)
                    elif not target.exists():
                        shutil.copy2(child, target)
                try:
                    legacy_dir.rmdir()
                except OSError:
                    pass
            paths.append(english_dir)
        return paths

    def save_template_category(
        self,
        template_name: str,
        category: str,
        filename: str,
        data: dict[str, Any],
    ) -> Path:
        """把某一类配置保存到模板目录下的对应子目录中。"""
        directory = self.template_dir(template_name) / category
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / filename
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return path

    def copy_template(self, source_name: str, target_name: str) -> Path:
        """复制整个模板目录到新模板名，并补齐配置子目录。"""
        source = self.flow_dir / source_name
        if not source.is_dir():
            raise FileNotFoundError(f"源模板目录不存在：{source}")
        target = self.template_dir(target_name)
        shutil.copytree(source, target, dirs_exist_ok=True)
        self.ensure_template_dirs(target_name)
        return target

    def delete_template(self, template_name: str) -> bool:
        """删除模板目录，仅允许删除 flow 目录下的直接子目录。"""
        target = self.flow_dir / template_name
        if target.resolve().parent != self.flow_dir.resolve():
            return False
        if not target.exists():
            return False
        shutil.rmtree(target)
        return True

    def save_page_config(self, page_name: str, data: dict[str, Any]) -> Path:
        path = self.page_config_path(page_name)
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return path

    def load_page_config(self, page_name: str) -> dict[str, Any]:
        path = self.page_config_path(page_name)
        if not path.exists():
            return {}
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}

    def save_template(self, template_name: str, data: dict[str, Any]) -> Path:
        directory = self.template_dir(template_name)
        path = directory / "template.yaml"
        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return path

    def load_template(self, template_name: str) -> dict[str, Any]:
        path = self.template_dir(template_name) / "template.yaml"
        if not path.exists():
            return {}
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
