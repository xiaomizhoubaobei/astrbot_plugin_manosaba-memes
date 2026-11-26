"""pytest 共享入口：导入即注册桩路径与插件包视图。"""

from .pkg_view import PACKAGE_VIEW_MODE as PACKAGE_VIEW_MODE
from .pkg_view import install as install

__all__ = ["PACKAGE_VIEW_MODE", "install"]
