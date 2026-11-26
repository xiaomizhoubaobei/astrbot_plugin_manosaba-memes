"""在同一进程内建立桩/包视图 → 启动 coverage → 跑 pytest。

不能直接用 ``coverage run --source=<包名> -m pytest``：coverage 在启动阶段
就解析 ``--source``，而包视图由 conftest/本模块建立，顺序不对会写出空报告。
本脚本把顺序倒过来，保证覆盖率口径命中仓库根源码。

用法::

    python -m tests.run_coverage                  # 跑测试 + 报告 + coverage.xml
    python -m tests.run_coverage -- -k models     # "--" 之后透传给 pytest
"""

from __future__ import annotations

import sys

from coverage import Coverage

# 关键顺序：先建桩路径与包视图，再构造 Coverage
from tests import pkg_view  # noqa: F401  导入即注册

PACKAGE_NAME = pkg_view.PACKAGE_NAME
REPO_ROOT = pkg_view.REPO_ROOT
_XML_PATH = REPO_ROOT / "coverage.xml"
_OMIT = ["tests/*", "*/tests/*"]
_PYTEST_ARGS = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["tests"]


def main() -> int:
    """运行测试、打印覆盖率报告并写 coverage.xml，返回退出码。"""
    cov = Coverage(source=[PACKAGE_NAME], omit=_OMIT, config_file=False)
    cov.start()
    try:
        import pytest

        code = pytest.main(["-q", *_PYTEST_ARGS])
    finally:
        cov.stop()
        cov.save()

    # 测试失败也出报告，便于分辨「用例挂」还是「口径挂」
    cov.report()
    cov.xml_report(outfile=str(_XML_PATH))
    print(f"[coverage] XML 已写出：{_XML_PATH}")
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
