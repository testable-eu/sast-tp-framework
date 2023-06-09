from pathlib import Path
import yaml
from typing import Dict
import sys

DIR: Path = Path(__file__).parent.resolve()
SAST_DIR: Path = DIR.parent.parent.resolve()
sys.path.append(str(SAST_DIR))

from codeql.core.codeql import CodeQL

class CodeQL_v_2_13_1(CodeQL):

    def __init__(self):
        self.tool = "codeql_2_13_1"
        self.CODEQL_SCRIPT_DIR: Path = Path(__file__).parent.resolve()
        self.CODEQL_CONFIG_FILE: Path = self.CODEQL_SCRIPT_DIR / "config.yaml"
        with open(self.CODEQL_CONFIG_FILE) as sast_config_file:
            self.CODEQL_CONFIG: Dict = yaml.load(sast_config_file, Loader=yaml.Loader)
