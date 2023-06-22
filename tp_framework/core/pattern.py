# import json
import shutil
from os import listdir
from pathlib import Path

from core.exceptions import PatternInvalid
from core.instance import Instance
from core.pattern_repair import PatternRepair
from core import utils
# from core.exceptions import LanguageTPLibDoesNotExist, PatternDoesNotExists, PatternValueError
from typing import Tuple



class Pattern:
    @classmethod
    def init_from_id_and_language(cls, id: int, language: str, tp_lib_path: Path):
        return cls._init_from_id_and_language(cls(), id, language.upper(), tp_lib_path)
    
    @classmethod
    def init_from_json_file_without_pattern_id(cls, json_file_path: Path, language: str, pattern_path: Path, tp_lib_path: Path):
        return cls._init_from_json_without_id(cls(), json_file_path, language, pattern_path, tp_lib_path)

    def __init__(self) -> None:
        # metadata
        self.pattern_id = None
        self.language = None # TODO: needed?
        self.tp_lib_path = None # TODO needed?
        self.language = None
        self.pattern_path = None
        self.pattern_json_path = None

        # json fields
        self.name = None
        self.description = None
        self.family = None
        self.tags = None
        self.version = None
        self.instances = []

        # repairing tools
        self.pattern_repair = None
    
    def _assert_pattern(self):
        try:
            assert int(self.pattern_id)
            assert self.language
            assert self.tp_lib_path.is_dir()
            assert self.pattern_path.is_dir()
            assert self.pattern_json_path.is_file()
            assert self.instances and all([isinstance(instance, Instance) for instance in self.instances])
        except Exception as e:
            raise PatternInvalid(f"{self._log_prefix()}Instance Variables are not properly set. '{e}'")

    def _init_from_id_and_language(self, id: int, language: str, tp_lib_path: Path):
        self.pattern_id = id
        self.language = language.upper()
        self.tp_lib_path = tp_lib_path
        self.pattern_path = utils.get_pattern_dir_from_id(id, language, tp_lib_path)
        self._init_from_json_file(utils.get_pattern_json(self.pattern_path))
        self._assert_pattern()
        return self
    
    def _init_instances(self, instance_paths_from_json: list):
        instances = []
        for instance_json in instance_paths_from_json:
            print('\033[93m', instance_json, '\033[0m')
            abs_path = Path(self.pattern_path / Path(instance_json))
            if not abs_path.is_file():
                raise PatternInvalid(f"{self._log_prefix()}The instance path '{instance_json}' is not valid.")
            instances += [Instance.init_from_json_path(abs_path, self.pattern_id)]
        instances = sorted(instances, key=lambda instance: instance.instance_id)
        return instances
    
    def _init_from_json_file(self, json_file_path: Path):
        self.pattern_json_path = json_file_path
        pattern_properties = utils.read_json(self.pattern_json_path)
        if not pattern_properties:
            raise PatternInvalid("The pattern needs a valid JSON file.")
        self.name = pattern_properties["name"] if "name" in pattern_properties.keys()  else None
        self.description = pattern_properties["description"] if "description" in pattern_properties.keys() else None
        self.family = pattern_properties["family"] if "family" in pattern_properties.keys() else None
        self.tags = pattern_properties["tags"] if "tags" in pattern_properties.keys() else None
        self.version = pattern_properties["version"] if "version" in pattern_properties.keys() else None
        if "instances" in pattern_properties.keys() and pattern_properties["instances"]:
            self.instances = self._init_instances(pattern_properties["instances"])
        else:
            # Raise exception
            raise PatternInvalid(f"{self._log_prefix()}Pattern JSON file needs an 'instances' key with valid relative links.")
        return self
    
    def _init_from_json_without_id(self, json_file_path: Path, language: str, pattern_path: Path, tp_lib_path: Path):
        self.language = language.upper()
        self.pattern_path = pattern_path
        self.tp_lib_path = tp_lib_path
        self._init_from_json_file(json_file_path)
        try:
            given_id = utils.get_id_from_name(self.pattern_path.name)
        except Exception:
            given_id = None
        free_id = utils.get_next_free_pattern_id_for_language(self.language, self.tp_lib_path, given_id)
        self.pattern_id = free_id
        self._assert_pattern()
        return self
    
    def _log_prefix(self):
        return f"Pattern {self.pattern_id} ({self.language}) - "
    
    def __str__(self) -> str:
        return str(vars(self))
    
    def copy_to_tplib(self) -> Path:
        # copies the pattern and all its instances into the tp_lib
        new_pattern_path = self.tp_lib_path / self.language / f'{self.pattern_id}_{self.pattern_path.name}'
        print(new_pattern_path)
        for instance in self.instances:
            instance.copy_to_tplib(new_pattern_path)
        utils.copy_dir_content(self.pattern_path, new_pattern_path)
        self.repair(soft=True)
    
    def repair(self, soft: bool = False):
        # soft repair enforces the instances structure (and names) and updates relative links in pattern JSON
        self.pattern_repair = PatternRepair(self)
        self.pattern_repair
        pass


def get_pattern_by_pattern_id(language: str, pattern_id: int, tp_lib_dir: Path) -> Tuple[Pattern, Path]:
    pattern = Pattern.init_from_id_and_language(pattern_id, language, tp_lib_dir)
    return pattern, pattern.pattern_path


# def pattern_from_dict(pattern_dict: Dict, language: str, pattern_id: int) -> Pattern:
#     try:
#         return Pattern(pattern_dict["name"], language, pattern_dict["instances"],
#                        family=pattern_dict.get("family", None),
#                        description=pattern_dict.get("description", ""),
#                        tags=pattern_dict.get("tags", []),
#                        pattern_id=pattern_id)
#     except KeyError as e:
#         raise PatternValueError(message=f"Key {e} was not found in pattern metadata")

# def get_pattern_path_by_pattern_id(language: str, pattern_id: int, tp_lib_dir: Path) -> Path:
#     tp_dir_for_language: Path = tp_lib_dir / language
#     filtered_res: list[str] = list(filter(
#         lambda x: x.split("_")[0] == str(pattern_id),
#         map(lambda y: y.name, utils.list_dirs_only(tp_dir_for_language))
#     ))
#     if not filtered_res:
#         raise PatternDoesNotExists(pattern_id)
#     return tp_dir_for_language / filtered_res[0]

# class Pattern:
#     def __init__(self, name: str, language: str, instances: list[Path], family: str = None, description: str = "",
#                  tags: list[str] = [], pattern_id: int = None, pattern_dir: Path = None) -> None:
#         self.name = name
#         self.description = description
#         self.family = family
#         self.tags = tags
#         self.instances = instances
#         self.language = language
#         self.pattern_id = pattern_id or self.define_pattern_id(pattern_dir)

#     def define_pattern_id(self, pattern_dir) -> int:
#         try:
#             dir_list: list[Path] = utils.list_pattern_paths_for_language(self.language, pattern_dir)
#         except LanguageTPLibDoesNotExist:
#             return 1
#         id_list: list[int] = sorted(list(map(lambda x: int(str(x.name).split("_")[0]), dir_list)))
#         return id_list[-1] + 1 if len(id_list) > 0 else 1

#     def add_pattern_to_tp_library(self, language: str, pattern_src_dir: Path, pattern_dir: Path) -> None:
#         pattern_dir_name: str = utils.get_pattern_dir_name_from_name(pattern_src_dir.name, self.pattern_id)
#         new_tp_dir: Path = pattern_dir / language / pattern_dir_name
#         new_tp_dir.mkdir(exist_ok=True, parents=True)
#         pattern_json_file: Path = new_tp_dir / f"{pattern_dir_name}.json"

#         with open(pattern_json_file, "w") as json_file:
#             pattern_dict: Dict = {
#                 "name": self.name,
#                 "description": self.description,
#                 "family": self.family,
#                 "tags": self.tags,
#                 "instances": self.instances,
#             }
#             json.dump(pattern_dict, json_file, indent=4)

#     def add_new_instance_reference(self, language: str, pattern_dir: Path, new_instance_ref: str) -> None:
#         tp_dir: Path = get_pattern_path_by_pattern_id(language, self.pattern_id, pattern_dir)
#         with open(tp_dir / f"{tp_dir.name}.json") as json_file:
#             pattern_dict: Dict = json.load(json_file)

#         pattern_dict["instances"].append(new_instance_ref)

#         with open(tp_dir / f"{tp_dir.name}.json", "w") as json_file:
#             json.dump(pattern_dict, json_file, indent=4)


# # TODO (old): Test this
# def get_pattern_by_pattern_id(language: str, pattern_id: int, tp_lib_dir: Path) -> Tuple[Pattern, Path]:
#     tp_dir: Path = get_pattern_path_by_pattern_id(language, pattern_id, tp_lib_dir)
#     tp_json: Path = tp_dir / f"{tp_dir.name}.json"
#     with open(tp_json) as json_file:
#         pattern_from_json: Dict = json.load(json_file)
#     return pattern_from_dict(pattern_from_json, language, pattern_id), tp_dir


# def get_pattern_path_by_pattern_id(language: str, pattern_id: int, tp_lib_dir: Path) -> Path:
#     tp_dir_for_language: Path = tp_lib_dir / language
#     filtered_res: list[str] = list(filter(
#         lambda x: x.split("_")[0] == str(pattern_id),
#         map(lambda y: y.name, utils.list_dirs_only(tp_dir_for_language))
#     ))
#     if not filtered_res:
#         raise PatternDoesNotExists(pattern_id)
#     return tp_dir_for_language / filtered_res[0]


# def pattern_from_dict(pattern_dict: Dict, language: str, pattern_id: int) -> Pattern:
#     try:
#         return Pattern(pattern_dict["name"], language, pattern_dict["instances"],
#                        family=pattern_dict.get("family", None),
#                        description=pattern_dict.get("description", ""),
#                        tags=pattern_dict.get("tags", []),
#                        pattern_id=pattern_id)
#     except KeyError as e:
#         raise PatternValueError(message=f"Key {e} was not found in pattern metadata")


if __name__ == '__main__':
    print(PatternR.init_from_id_and_language(1, 'php', Path('./testability_patterns')))
