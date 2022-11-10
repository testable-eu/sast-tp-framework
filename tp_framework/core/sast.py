import abc
from pathlib import Path
from typing import Dict


class SAST(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, "launcher") and callable(subclass.launcher) and
                hasattr(subclass, "inspector") and callable(subclass.inspector) and
                hasattr(subclass, "get_tool_version") and callable(subclass.get_tool_version) and
                hasattr(subclass, "logger") and callable(subclass.logger) or
                NotImplemented)

    @abc.abstractmethod
    async def launcher(self, src_dir: Path, language: str, **kwargs) -> Path:
        raise NotImplementedError

    @abc.abstractmethod
    def inspector(self, sast_res_file: Path, language: str) -> list[Dict]:
        """
        Shall return a list of Dict s.t. :
        [{
            type: "",
            file: "",
            line: ""
        }, ...]
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_tool_version(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def logger(self) -> None:
        raise NotImplementedError
