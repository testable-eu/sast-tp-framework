import abc
from pathlib import Path
from typing import Dict
from datetime import datetime

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

from core import utils


class SAST(metaclass=abc.ABCMeta):
    tool = None

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, "launcher") and callable(subclass.launcher) and
                hasattr(subclass, "inspector") and callable(subclass.inspector) and
                hasattr(subclass, "get_tool_version") and callable(subclass.get_tool_version) or
                NotImplemented)


    @abc.abstractmethod
    async def launcher(self, src_dir: Path, language: str, output_dir: Path, **kwargs) -> Path:
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


    @staticmethod
    def build_project_name(name: str, tool: str | None, language: str, timestamp: bool = True):
        now = None
        if timestamp:
            now = datetime.now()
        if tool:
            comp = f"{tool}_{name}"
        else:
            comp = name
        return utils.build_timestamp_language_name(comp, language, now, extra="TPF")


    def logging(self, what="launcher", message=None, status=None):
        messagestr = ""
        if message:
            messagestr = f" - {message}"
        statusstr = ""
        if status:
            statusstr = f": {status}"
        logger.info(f"SAST tool {self.tool} - {what}{messagestr}{statusstr}")


    @staticmethod
    def get_norm_vuln(vuln: str, d_supported_vuln_map: Dict):
        for norm_vuln in d_supported_vuln_map:
            if SAST.vuln_match(d_supported_vuln_map[norm_vuln], vuln):
                return norm_vuln
        return None


    @staticmethod
    # simple sub-string but it could be elaborated more
    def vuln_match(vcand, vtarget):
        return vcand in vtarget
