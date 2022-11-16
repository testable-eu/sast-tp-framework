import asyncio
from json import JSONDecodeError
from typing import Dict

import config
from pathlib import Path

from cli.measure_pattern import measure_list_patterns
from core import pattern_operations, utils
from core.exceptions import PatternValueError


def add_pattern(pattern_dir: str, language: str, measure: bool, tools: list[Dict], pattern_json: str = None,
                pattern_lib_dir: str = config.DEFAULT_TP_LIBRARY_ROOT_DIR):
    pattern_dir_path: Path = Path(pattern_dir).resolve()
    if not pattern_dir_path.is_dir():
        print(f"`{pattern_dir_path}` not found or is not a folder.")
        return

    if not pattern_json:
        pattern_json_path: Path = pattern_dir_path / f"{pattern_dir_path.name}.json"
        if not pattern_json_path.exists():
            print(
                f"`{pattern_json_path}` metadata not found in folder. Please specify explicitly a file containing the pattern metadata.")
            return
    else:
        pattern_json_path: Path = Path(pattern_json).resolve()

    pattern_lib_dir_path: Path = Path(pattern_lib_dir).resolve()
    pattern_lib_dir_path.mkdir(exist_ok=True, parents=True)

    try:
        created_pattern_path: Path = pattern_operations.add_testability_pattern_to_lib_from_json(
            language,
            pattern_json_path,
            pattern_dir_path,
            pattern_lib_dir_path
        )
        created_pattern_id: int = utils.get_id_from_name(created_pattern_path.name)
    except PatternValueError as e:
        print(e)
        raise
    except JSONDecodeError as e:
        print(e)
        raise
    except Exception as e:
        print(e)
        raise

    for t in tools:
        t["supported_languages"] = config.load_sast_specific_config(t["name"], t["version"])["supported_languages"]

    tools = list(filter(lambda x: language in x["supported_languages"], tools))

    if measure:
        asyncio.run(measure_list_patterns([created_pattern_id], language, tools, pattern_lib_dir))
