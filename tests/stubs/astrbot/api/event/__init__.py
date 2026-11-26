"""astrbot.api.event 桩：事件基类与命令/正则过滤器装饰器。"""

from typing import Any, Callable


class AstrMessageEvent:
    """事件基类桩；测试里用更具体的假事件替身。"""

    message_str: str = ""

    def plain_result(self, text: str) -> Any:
        """Return a stub plain-text result."""
        return ("plain", text)

    def image_result(self, path: str) -> Any:
        """Return a stub image result."""
        return ("image", path)

    def get_session_id(self) -> str:
        """Return a stub session identifier."""
        return "session"


class _Filter:
    """过滤器桩：命令/正则装饰器原样返回函数，附带元信息供测试断言。"""

    @staticmethod
    def _decorator(kind: str, *args: Any, **kwargs: Any) -> Callable[[Any], Any]:
        def wrap(func: Any) -> Any:
            func.__decorator_meta__ = {"type": kind, "args": args, "kwargs": kwargs}
            return func

        return wrap

    @classmethod
    def command(cls, *args: Any, **kwargs: Any) -> Callable[[Any], Any]:
        return cls._decorator("command", *args, **kwargs)

    @classmethod
    def regex(cls, *args: Any, **kwargs: Any) -> Callable[[Any], Any]:
        return cls._decorator("regex", *args, **kwargs)


filter = _Filter()
