from pathlib import Path
from typing import Dict

import core.utils
from core import utils
from core.sast import SAST


async def scan(src_dir: Path, tools: list[Dict], language: str, modelling_rules: Path = None):
    if not src_dir.is_dir():
        raise
    if not tools:
        raise
    
    results = []
    for tool in tools:
        sast_config: Dict = core.utils.load_sast_specific_config(tool["name"], tool["version"])
        sast_interface_class: str = sast_config["tool_interface"]
        sast_class = utils.get_class_from_str(sast_interface_class)

        # noinspection PyCallingNonCallable
        sast: SAST = sast_class()
        res = await sast.launcher(src_dir, language, output_dir, use_mvn=(src_dir / "pom.xml").exists(),
                                  apply_remediation=True, modelling_rules=modelling_rules)

        results.append({f"{tool['name']}:{tool['version']}": sast.inspector(res, language)})
    return results, tools
