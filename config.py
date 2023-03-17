from pathlib import Path
from typing import Dict

import yaml

# IMPORTANT: Change some of these parameters may affect the docker-compose and related Dockerfiles.
#            Be sure you retrofit your changes there as well.

## General
RESULT_REL_DIR = "out"
TP_LIB_REL_DIR = "testability_patterns"
MEASUREMENT_REL_DIR = "measurements"
ROOT_DIR: Path = Path(__file__).parent
RESULT_DIR: Path = ROOT_DIR / RESULT_REL_DIR
DEFAULT_TP_LIBRARY_ROOT_DIR: Path = ROOT_DIR / TP_LIB_REL_DIR
WORKERS = 5

## Logging
logfile = 'tpframework.log'
rootLoggerName = "tpframework"
loggingLevelFile = 'DEBUG'
loggingLevelConsole = 'INFO'

## SAST
ROOT_SAST_DIR: Path = ROOT_DIR / "SAST"
SAST_CONFIG_FILE: Path = ROOT_SAST_DIR / "sast-config.yaml"
SAST_TOOLS_ENABLED: list[Dict] = [
    {
        "name": "codeql",
        "version": "2.9.2"
    }
]

## Discovery
_ROOT_JOERN_CPG_GEN_DIR: Path = ROOT_DIR / "discovery/joern"
JOERN_CPG_GEN_CONFIG_FILE: Path = _ROOT_JOERN_CPG_GEN_DIR / "cpg-gen-config.yaml"

DEFAULT_DISCOVERY_METHOD = "joern"
DISCOVERY_RULE_MAPPING = {
    "joern": ".sc"
}

PATCHED_PREFIX = "__P@TCHED__"
