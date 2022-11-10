import sys
from pathlib import Path
from typing import Dict

import config
from core import discovery
from core.exceptions import DiscoveryMethodNotSupported, CPGGenerationError, CPGLanguageNotSupported


def run_discovery_for_all_patterns(src_dir: str, language: str, tools: list[Dict],
                                   tp_lib_dir: str = config.DEFAULT_TP_LIBRARY_ROOT_DIR):
    tp_lib_dir_path: Path = Path(tp_lib_dir).resolve()
    if not tp_lib_dir_path.is_dir():
        print(f"Specified `{tp_lib_dir}` is not a folder or does not exists", file=sys.stderr)
        return

    meas_lang_lib_dir_path: Path = tp_lib_dir_path / "measurements" / language
    if not meas_lang_lib_dir_path.is_dir():
        print(f"Specified language folder`{meas_lang_lib_dir_path}` does not exists", file=sys.stderr)
        return

    all_patterns_id_list: list[int] = list(
        map(lambda d: int(d.name.split("_")[0]), list(meas_lang_lib_dir_path.iterdir())))

    for t in tools:
        t["supported_languages"] = config.load_sast_specific_config(t["name"], t["version"])["supported_languages"]

    tools = list(filter(lambda x: language in x["supported_languages"], tools))

    discovery.discovery(Path(src_dir).resolve(), all_patterns_id_list, tp_lib_dir_path, tools, language)


def run_discovery_for_pattern_list(src_dir: str, pattern_id_list: list[int], language: str, tools: list[Dict],
                                   tp_lib_dir: str = config.DEFAULT_TP_LIBRARY_ROOT_DIR):
    tp_lib_dir_path: Path = Path(tp_lib_dir).resolve()
    if not tp_lib_dir_path.is_dir():
        print(f"Specified `{tp_lib_dir}` is not a folder or does not exists", file=sys.stderr)
        return

    for t in tools:
        t["supported_languages"] = config.load_sast_specific_config(t["name"], t["version"])["supported_languages"]

    tools = list(filter(lambda x: language in x["supported_languages"], tools))

    discovery.discovery(Path(src_dir).resolve(), pattern_id_list, tp_lib_dir_path, tools, language)


def manual_discovery(src_dir: str, discovery_method: str, discovery_rule_list: list[str], language: str, timeout_sec: int):
    match discovery_method:
        case "joern":
            src_dir_path: Path = Path(src_dir).resolve()
            discovery_rules_to_run: list[Path] = []
            for discovery_rule in discovery_rule_list:
                discovery_rule_path = Path(discovery_rule).resolve()
                if discovery_rule_path.is_dir():
                    for p in discovery_rule_path.glob('**/*'):
                        discovery_rules_to_run.append(p)
                else:
                    discovery_rules_to_run.append(discovery_rule_path)
            discovery_rules_to_run = list(filter(lambda r: r.suffix == ".sc", discovery_rules_to_run))
            try:
                discovery.manual_discovery(src_dir_path, discovery_method, discovery_rules_to_run, language, timeout_sec)
            except (CPGGenerationError, CPGLanguageNotSupported) as e:
                print(e)
        case _:
            raise DiscoveryMethodNotSupported(discovery_method=discovery_method)

