from pathlib import Path
from typing import Dict

import yaml

ROOT_DIR: Path = Path(__file__).parent
_SAST_CONFIG_FILE: Path = ROOT_DIR / "SAST/sast-config.yaml"
_ROOT_SAST_DIR: Path = ROOT_DIR / "SAST"
RESULT_DIR: Path = ROOT_DIR / "out"


def _load_sast_config() -> Dict:
    with open(_SAST_CONFIG_FILE) as sast_conf_file:
        sast_conf: Dict = yaml.load(sast_conf_file, Loader=yaml.Loader)
    return sast_conf


SAST_CONFIG: Dict = _load_sast_config()
DEFAULT_TP_LIBRARY_ROOT_DIR: Path = ROOT_DIR / "testability_patterns"


def load_sast_specific_config(tool_name: str, tool_version: str) -> Dict:
    tool_config_path: Path = _ROOT_SAST_DIR / SAST_CONFIG["tools"][tool_name]["version"][tool_version]["config"]
    with open(tool_config_path) as sast_config_file:
        sast_specific_config: Dict = yaml.load(sast_config_file, Loader=yaml.Loader)

    return sast_specific_config


_ROOT_JOERN_CPG_GEN_DIR: Path = ROOT_DIR / "discovery/joern"
_JOERN_CPG_GEN_CONFIG_FILE: Path = ROOT_DIR / "discovery/joern/cpg-gen-config.yaml"


def _load_cpg_gen_config() -> Dict:
    with open(_JOERN_CPG_GEN_CONFIG_FILE) as conf_file:
        conf: Dict = yaml.load(conf_file, Loader=yaml.Loader)
    return conf


CPG_GEN_CONFIG: Dict = _load_cpg_gen_config()
