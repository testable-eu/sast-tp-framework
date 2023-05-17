import json
from pathlib import Path
from core import utils
from core.exceptions import LanguageTPLibDoesNotExist, PatternDoesNotExists, PatternValueError
from typing import Dict, Tuple


class Pattern:
    def __init__(self, name: str, language: str, instances: list[Path], family: str = None, description: str = "",
                 tags: list[str] = [], pattern_id: int = None, pattern_dir: Path = None) -> None:
        self.name = name
        self.description = description
        self.family = family
        self.tags = tags
        self.instances = instances
        self.language = language
        self.pattern_id = pattern_id or self.define_pattern_id(pattern_dir)

    def define_pattern_id(self, pattern_dir) -> int:
        try:
            dir_list: list[Path] = utils.list_pattern_paths_for_language(self.language, pattern_dir)
        except LanguageTPLibDoesNotExist:
            return 1
        id_list: list[int] = sorted(list(map(lambda x: int(str(x.name).split("_")[0]), dir_list)))
        return id_list[-1] + 1 if len(id_list) > 0 else 1

    def add_pattern_to_tp_library(self, language: str, pattern_src_dir: Path, pattern_dir: Path) -> None:
        pattern_dir_name: str = utils.get_pattern_dir_name_from_name(pattern_src_dir.name, self.pattern_id)
        new_tp_dir: Path = pattern_dir / language / pattern_dir_name
        new_tp_dir.mkdir(exist_ok=True, parents=True)
        pattern_json_file: Path = new_tp_dir / f"{pattern_dir_name}.json"

        with open(pattern_json_file, "w") as json_file:
            pattern_dict: Dict = {
                "name": self.name,
                "description": self.description,
                "family": self.family,
                "tags": self.tags,
                "instances": self.instances,
            }
            json.dump(pattern_dict, json_file, indent=4)

    def add_new_instance_reference(self, language: str, pattern_dir: Path, new_instance_ref: str) -> None:
        tp_dir: Path = get_pattern_path_by_pattern_id(language, self.pattern_id, pattern_dir)
        with open(tp_dir / f"{tp_dir.name}.json") as json_file:
            pattern_dict: Dict = json.load(json_file)

        pattern_dict["instances"].append(new_instance_ref)

        with open(tp_dir / f"{tp_dir.name}.json", "w") as json_file:
            json.dump(pattern_dict, json_file, indent=4)


# TODO (old): Test this
def get_pattern_by_pattern_id(language: str, pattern_id: int, tp_lib_dir: Path) -> Tuple[Pattern, Path]:
    tp_dir: Path = get_pattern_path_by_pattern_id(language, pattern_id, tp_lib_dir)
    tp_json: Path = tp_dir / f"{tp_dir.name}.json"
    with open(tp_json) as json_file:
        pattern_from_json: Dict = json.load(json_file)
    return pattern_from_dict(pattern_from_json, language, pattern_id), tp_dir


def get_pattern_path_by_pattern_id(language: str, pattern_id: int, tp_lib_dir: Path) -> Path:
    tp_dir_for_language: Path = tp_lib_dir / language
    filtered_res: list[str] = list(filter(
        lambda x: x.split("_")[0] == str(pattern_id),
        map(lambda y: y.name, utils.list_dirs_only(tp_dir_for_language))
    ))
    if not filtered_res:
        raise PatternDoesNotExists(pattern_id)
    return tp_dir_for_language / filtered_res[0]


def pattern_from_dict(pattern_dict: Dict, language: str, pattern_id: int) -> Pattern:
    try:
        return Pattern(pattern_dict["name"], language, pattern_dict["instances"],
                       family=pattern_dict.get("family", None),
                       description=pattern_dict.get("description", ""),
                       tags=pattern_dict.get("tags", []),
                       pattern_id=pattern_id)
    except KeyError as e:
        raise PatternValueError(message=f"Key {e} was not found in pattern metadata")
