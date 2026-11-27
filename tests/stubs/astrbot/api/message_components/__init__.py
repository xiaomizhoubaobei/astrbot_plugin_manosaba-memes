"""astrbot.api.message_components stub: image components used by tests."""

import base64


class Image:
    """Image component carrying a base64 data URI."""

    def __init__(self, file: str) -> None:
        self.file = file

    @staticmethod
    def fromBytes(data: bytes) -> "Image":
        """Build an image component from raw bytes."""
        return Image("base64://" + base64.b64encode(data).decode())
