"""建立插件包视图：把仓库根暴露为顶层包名 ``astrbot_plugin_manosaba_memes``。

本仓库 ``__init__.py`` 在仓库根（包根=检出根），但检出目录未必叫包名。
这里注册一个 meta path finder，把仓库根以固定包名暴露给 import 系统，
使测试导入与 ``coverage --source`` 都不依赖检出目录名。

注意：不要在这里注入 ``tests/stubs``。新测试需要真实的 sketchbook 与
Pillow 渲染（用 PIL 打开产出的 PNG 校验），假桩会产出不可解析的假 PNG；
AstrBot 宿主的桩由 ``tests/conftest.py`` 负责注册。
"""

from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import pathlib
import sys
from types import ModuleType
from typing import Optional, Sequence

PACKAGE_NAME = "astrbot_plugin_manosaba_memes"
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


class _PackageAliasFinder(importlib.abc.MetaPathFinder):
    """把 package_root 以 package_name 暴露给 import 系统。"""

    def __init__(self, package_name: str, package_root: str) -> None:
        self.package_name = package_name
        self.package_root = package_root

    def find_spec(
        self,
        fullname: str,
        path: Optional[Sequence[str]] = None,
        target: Optional[ModuleType] = None,
    ) -> Optional[importlib.machinery.ModuleSpec]:
        if fullname != self.package_name:
            return None
        return importlib.util.spec_from_file_location(
            fullname,
            f"{self.package_root}/__init__.py",
            submodule_search_locations=[self.package_root],
        )


def install() -> str:
    """注册包视图（幂等），返回策略名。"""
    if PACKAGE_NAME in sys.modules:
        return "existing"
    # 已经注册过就不重复插入
    for finder in sys.meta_path:
        if getattr(finder, "package_root", None) == str(REPO_ROOT):
            return "alias"
    sys.meta_path.insert(0, _PackageAliasFinder(PACKAGE_NAME, str(REPO_ROOT)))
    return "alias"


PACKAGE_VIEW_MODE: str = install()

# 便于测试读取
__all__ = ["PACKAGE_NAME", "REPO_ROOT", "PACKAGE_VIEW_MODE", "install"]
