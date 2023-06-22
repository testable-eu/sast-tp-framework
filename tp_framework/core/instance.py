import json
import shutil
from pathlib import Path
from os import listdir

from core import utils
from core.exceptions import InstanceInvalid

class Instance:
    @classmethod
    def init_from_json_path(cls, path_to_instance_json: Path, pattern_id=None):
        if not path_to_instance_json.is_file():
            raise InstanceInvalid(f"The provided instance path '{path_to_instance_json}' does not exist.")
        return cls._init_from_json(cls(), path_to_instance_json, pattern_id)
    
    def __init__(self) -> None:
        self.instance_path = None
        self.instance_json_path = None
        self.instance_id = None
        self.pattern_id = None

        # JSON fields
        self.description = None
        self.code_path = None
        self.code_injection_skeleton_broken = None
        self.expectation_type = None
        self.expectation_sink_file = None
        self.expectation_sink_line = None
        self.expectation_source_file = None
        self.expectation_source_line = None
        self.expectation_expectation = None
        self.compile_binary = None
        self.compile_instruction = None
        self.compile_dependencies = None
        self.discovery_rule = None
        self.discovery_method = None
        self.discovery_rule_accuracy = None
        self.discovery_notes = None
        self.properties_category = None
        self.properties_feature_vs_internal_api = None
        self.properties_input_sanitizer = None
        self.properties_source_and_sink = None
        self.properties_negative_test_case = None
        self.remediation_notes = None
        self.remediation_transformation = None
        self.remediation_modeling_rule = None

        self.attributes_with_type_path = ['instance_path', 'instance_json_path']

    def _assert_instance(self):
        try:
            int(self.instance_id)
            int(self.pattern_id)
            assert self.instance_path.is_dir()
            assert self.instance_json_path.is_file()
            assert self.code_path.is_file()
        except Exception as e:
            raise InstanceInvalid(f"{self._log_prefix()}Instance Variables are not properly set. '{e}'")

    def _init_from_json(self, path_to_instance_json: Path, pattern_id):
        self.instance_path = path_to_instance_json.parent
        self.instance_json_path = Path(path_to_instance_json.name)
        try:
            self.instance_id = utils.get_id_from_name(self.instance_path.name)
        except Exception as e:
            raise InstanceInvalid(f"Could not get id from '{self.instance_path.name}'.")
        
        self.pattern_id = pattern_id

        # enforced values
        instance_properties = utils.read_json(self.instance_json_path)
        if not instance_properties:
            raise InstanceInvalid(f"{self._log_prefix()}Please check {self.instance_json_path}.")
        
        self.description = instance_properties.get("description", None)
        self.code_path = Path(instance_properties.get("code", {}).get("path", None))
        self.code_injection_skeleton_broken = instance_properties.get("code", {}).get("injection_skeleton_broken", None)
        self.expectation_type = instance_properties.get("expectation", {}).get("type", None)
        self.expectation_sink_file = Path(instance_properties.get("expectation", {}).get("sink_file", None))
        self.expectation_sink_line = instance_properties.get("expectation", {}).get("sink_line", None)
        self.expectation_source_file = Path(instance_properties.get("expectation", {}).get("source_file", None))
        self.expectation_source_line = instance_properties.get("expectation", {}).get("source_line", None)
        self.expectation_expectation = instance_properties.get("expectation", {}).get("expectation", None)
        self.compile_binary = instance_properties.get("compile", {}).get("binary", None)
        self.compile_instruction = instance_properties.get("compile", {}).get("instruction", None)
        self.compile_dependencies = instance_properties.get("compile", {}).get("dependencies", None)
        self.discovery_rule = Path(instance_properties.get("discovery", {}).get("rule", None))
        self.discovery_method = instance_properties.get("discovery", {}).get("method", None)
        self.discovery_rule_accuracy = instance_properties.get("discovery", {}).get("rule_accuracy", None)
        self.discovery_notes = instance_properties.get("discovery", {}).get("notes", None)
        self.properties_category = instance_properties.get("properties", {}).get("category", None)
        self.properties_feature_vs_internal_api = instance_properties.get("properties", {}).get("feature_vs_internal_api", None)
        self.properties_input_sanitizer = instance_properties.get("properties", {}).get("input_sanitizer", None)
        self.properties_source_and_sink = instance_properties.get("properties", {}).get("source_and_sink", None)
        self.properties_negative_test_case = instance_properties.get("properties", {}).get("negative_test_case", None)
        self.remediation_notes = instance_properties.get("remediation", {}).get("notes", None)
        self.remediation_transformation = instance_properties.get("remediation", {}).get("transformation", None)
        self.remediation_modeling_rule = instance_properties.get("remediation", {}).get("modeling_rule", None)
        return self
    
    def __getattribute__(self, name):
        base_path = super().__getattribute__("instance_path")
        attr = super().__getattribute__(name)
        if isinstance(attr, Path) and attr != base_path:
            attr = base_path / attr
        return attr

    def _log_prefix(self):
        return f"Pattern {self.pattern_id} - Instance {self.instance_id} - "

    def _make_path(self, path_name: str):
        return Path(self.instance_path / path_name).resolve() if path_name else None

    def __str__(self) -> str:
        return f"Instance {self.instance_id}"

    def copy_to_tplib(self, pattern_path: Path):
        new_instance_path = pattern_path / self.instance_path.name
        new_instance_path.mkdir(parents=True, exist_ok=True)
        utils.copy_dir_content(self.instance_path, new_instance_path)
        self.instance_path = new_instance_path


if __name__ == "__main__":
    p = Path(__file__).parent.parent.parent / 'testability_patterns' / 'PHP' / '1_static_variables' / '1_instance_1_static_variables' / '1_instance_1_static_variables.json'
    i = Instance.init_from_json_path(p, 1)
    print('\033[92m', i.code_path, '\033[0m')
    i.instance_path = "/tmp"
    print('\033[92m', i.code_path, '\033[0m')

# import json
# from enum import Enum
# from pathlib import Path
# from typing import Dict

# from core import utils
# from core.exceptions import PatternDoesNotExists, InstanceDoesNotExists
# from core.pattern import Pattern, get_pattern_path_by_pattern_id, get_pattern_by_pattern_id

# import logging
# from core import loggermgr

# logger = logging.getLogger(loggermgr.logger_name(__name__))

# class PatternCategory(str, Enum):
#     S0 = "S0"
#     D1 = "D1"
#     D2 = "D2"
#     D3 = "D3"
#     D4 = "D4"


# class FeatureVsInternalApi(str, Enum):
#     FEATURE = "FEATURE"
#     INTERNAL_API = "INTERNAL_API"


# class Instance(Pattern):
#     # TODO - pattern instance: update to current structure 09/2022
#     '''
#     '''

#     def __init__(
#             self,
#             code_path: Path,
#             code_injection_skeleton_broken: bool,
#             compile_dependencies: Path, # added 092022
#             compile_binary: Path,
#             compile_instruction: str, # added 092022
#             remediation_transformation: str, # added 092022
#             remediation_modeling_rule: Path, # added 092022
#             remediation_notes: str, # added 092022
#             properties_category: PatternCategory,
#             properties_negative_test_case: bool,
#             properties_source_and_sink: bool,
#             properties_input_sanitizer: bool,
#             properties_feature_vs_internal_api: FeatureVsInternalApi,
#             discovery_rule: Path,
#             discovery_method: str,
#             discovery_rule_accuracy: str,
#             discovery_notes: str,
#             expectation: bool,
#             expectation_type: str,
#             expectation_sink_file: Path,
#             expectation_sink_line: int,
#             expectation_source_file: Path,
#             expectation_source_line: int,
#             name: str,
#             description: str,
#             family: str,
#             tags: list[str],
#             instances: list[Path],
#             language: str,
#             pattern_id: int = None,
#             instance_id: int = None,
#             pattern_dir: Path = None,
#     ) -> None:
#         if pattern_id is None:
#             super().__init__(name, language, instances, family, description, tags, pattern_dir=pattern_dir)
#         else:
#             super().__init__(name, language, instances, family, description, tags, pattern_id)

#         self.code_injection_skeleton_broken = code_injection_skeleton_broken
#         self.compile_dependencies = compile_dependencies # added 092022
#         self.compile_binary = compile_binary
#         self.compile_instruction = compile_instruction  # added 092022
#         self.remediation_transformation = remediation_transformation  # added 092022
#         self.remediation_modeling_rule = remediation_modeling_rule # added 092022
#         self.remediation_notes = remediation_notes  # added 092022
#         self.properties_category = properties_category
#         self.properties_negative_test_case = properties_negative_test_case
#         self.properties_source_and_sink = properties_source_and_sink
#         self.properties_input_sanitizer = properties_input_sanitizer
#         self.properties_feature_vs_internal_api = properties_feature_vs_internal_api
#         self.expectation = expectation
#         self.discovery_rule = discovery_rule
#         self.discovery_method = discovery_method
#         self.discovery_rule_accuracy = discovery_rule_accuracy
#         self.discovery_notes = discovery_notes
#         self.expectation_type = expectation_type
#         self.expectation_sink_file = expectation_sink_file
#         self.expectation_sink_line = expectation_sink_line
#         self.expectation_source_file = expectation_source_file
#         self.expectation_source_line = expectation_source_line
#         self.instance_id = instance_id or self.define_instance_id(pattern_dir)
#         if code_path is None:
#             logger.warning("Instance without code snippet cannot even be measured by SAST tools: pattern {0}, instance {1}".format(name, instance_id))
#             self.code_path = ""
#         else:
#             self.code_path = code_path


#     def define_instance_id(self, pattern_dir: Path) -> int:
#         try:
#             inst_list: list[Path] = utils.list_tpi_paths_by_tp_id(
#                 self.language, self.pattern_id, pattern_dir)
#             id_list: list[int] = sorted(list(map(lambda x: int(str(x.name).split("_")[0]), inst_list)))
#             return id_list[-1] + 1 if len(id_list) > 0 else 1
#         except PatternDoesNotExists:
#             return 1

#     def add_instance_to_pattern_id(self, language: str, pattern_src_dir: Path, pattern_dir: Path) -> None:
#         instance_dir_name: str = utils.get_instance_dir_name_from_pattern(pattern_src_dir.name, self.pattern_id,
#                                                                           self.instance_id)
#         pattern_dir_name: str = utils.get_pattern_dir_name_from_name(pattern_src_dir.name, self.pattern_id)
#         instance_dir: Path = pattern_dir / language / pattern_dir_name / instance_dir_name
#         instance_dir.mkdir(exist_ok=True, parents=True)
#         instance_json_file: Path = instance_dir / f"{instance_dir_name}.json"

#         with open(instance_json_file, "w") as json_file:
#             instance_dict: Dict = {
#                 "code": {
#                     "path": utils.get_relative_path_str_or_none(self.code_path),
#                     "injection_skeleton_broken": self.code_injection_skeleton_broken
#                 },
#                 "remediation": {
#                     "notes": self.remediation_notes,
#                     "transformation": self.remediation_transformation,
#                     "modeling_rule": utils.get_relative_path_str_or_none(self.remediation_modeling_rule)
#                 },
#                 "discovery": {
#                     "rule": utils.get_relative_path_str_or_none(self.discovery_rule),
#                     "method": self.discovery_method,
#                     "rule_accuracy": self.discovery_rule_accuracy,
#                     "notes": self.discovery_notes
#                 },
#                 "compile": {
#                     "binary": utils.get_relative_path_str_or_none(self.compile_binary),
#                     "dependencies": utils.get_relative_path_str_or_none(self.compile_dependencies),
#                     "instruction": self.compile_instruction
#                 },
#                 "expectation": {
#                     "type": self.expectation_type,
#                     "sink_file": utils.get_relative_path_str_or_none(self.expectation_sink_file),
#                     "sink_line": self.expectation_sink_line,
#                     "source_file": utils.get_relative_path_str_or_none(self.expectation_source_file),
#                     "source_line": self.expectation_source_line,
#                     "expectation": self.expectation
#                 },
#                 "properties": {
#                     "category": utils.get_enum_value_or_none(self.properties_category),
#                     "feature_vs_internal_api": utils.get_enum_value_or_none(self.properties_feature_vs_internal_api),
#                     "input_sanitizer": self.properties_input_sanitizer,
#                     "source_and_sink": self.properties_source_and_sink,
#                     "negative_test_case": self.properties_negative_test_case
#                 }
#             }
#             json.dump(instance_dict, json_file, indent=4)


# # TODO (old): Test this
# def get_instance_by_instance_id(language: str, instance_id: int, pattern_id, pattern_dir: Path) -> Instance:
#     instance_dir: Path = get_instance_path_from_instance_id(language, pattern_id, instance_id, pattern_dir)
#     instance_json: Path = instance_dir / f"{instance_dir.name}.json"
#     with open(instance_json) as json_file:
#         pattern_from_json: Dict = json.load(json_file)

#     pattern, p_dir = get_pattern_by_pattern_id(language, pattern_id, pattern_dir)
#     return instance_from_dict(pattern_from_json, pattern, language, pattern_id)


# def get_instance_path_from_instance_id(language: str, pattern_id: int, instance_id: int, pattern_dir: Path) -> Path:
#     pattern_path: Path = get_pattern_path_by_pattern_id(language, pattern_id, pattern_dir)
#     filtered_res: list[str] = list(filter(
#         lambda x: int(x.split("_")[0]) == instance_id,
#         map(lambda y: y.name, utils.list_dirs_only(pattern_path))
#     ))
#     if not filtered_res:
#         raise InstanceDoesNotExists(instance_id)
#     return pattern_path / filtered_res[0]


# def instance_from_dict(instance_dict: Dict, pattern: Pattern, language: str, instance_id: int) -> Instance:
#     return Instance(
#         utils.get_path_or_none(utils.get_from_dict(instance_dict, "code", "path")),  # code_path: Path,
#         utils.get_from_dict(instance_dict, "code", "injection_skeleton_broken"),  # code_injection_skeleton_broken: bool,
#         utils.get_path_or_none(utils.get_from_dict(instance_dict, "compile", "dependencies")),  # compile_dependencies: Path, # added 092022
#         utils.get_path_or_none(utils.get_from_dict(instance_dict, "compile", "binary")),  # compile_binary: Path,
#         utils.get_from_dict(instance_dict, "compile", "instruction"),  # compile_instruction: str,  # added 092022
#         utils.get_from_dict(instance_dict, "remediation", "transformation"),  # remediation_transformation: str, # added 092022
#         utils.get_path_or_none(utils.get_from_dict(instance_dict, "remediation", "modeling_rule")),  # remediation_modeling_rule: Path, # added 092022
#         utils.get_from_dict(instance_dict, "remediation", "notes"),  # remediation_notes: str, # added 092022
#         get_pattern_category_or_none(utils.get_from_dict(instance_dict, "properties", "category")),
#         utils.get_from_dict(instance_dict, "properties", "negative_test_case"),
#         utils.get_from_dict(instance_dict, "properties", "source_and_sink"),
#         utils.get_from_dict(instance_dict, "properties", "input_sanitizer"),
#         get_feature_vs_internal_api_or_none(utils.get_from_dict(instance_dict, "properties", "feature_vs_internal_api")),
#         utils.get_path_or_none(utils.get_from_dict(instance_dict, "discovery", "rule")),
#         utils.get_from_dict(instance_dict, "discovery", "method"),
#         utils.get_from_dict(instance_dict, "discovery", "rule_accuracy"),
#         utils.get_from_dict(instance_dict, "discovery", "notes"),
#         utils.get_from_dict(instance_dict, "expectation", "expectation"),
#         utils.get_from_dict(instance_dict, "expectation", "type"),
#         utils.get_path_or_none(utils.get_from_dict(instance_dict, "expectation", "sink_file")),
#         utils.get_from_dict(instance_dict, "expectation", "sink_line"),
#         utils.get_path_or_none(utils.get_from_dict(instance_dict, "expectation", "source_file")),
#         utils.get_from_dict(instance_dict, "expectation", "source_line"),
#         pattern.name,
#         pattern.description,
#         pattern.family,
#         pattern.tags,
#         pattern.instances,
#         language,
#         pattern_id=pattern.pattern_id,
#         instance_id=instance_id
#     )


# def load_instance_from_metadata(metadata: str, tp_lib: Path, language: str) -> Instance:
#     metadata_path: Path = tp_lib / metadata
#     if not metadata_path.exists():
#         raise InstanceDoesNotExists(ref_metadata=metadata_path.name)

#     with open(metadata_path) as file:
#         try:
#             instance: Dict = json.load(file)
#         except Exception as e:
#             raise e

#     pattern_id = utils.get_id_from_name(metadata_path.parent.parent.name)
#     pattern, p_dir = get_pattern_by_pattern_id(language, pattern_id, tp_lib)
#     instance_id = utils.get_id_from_name(metadata_path.parent.name)
#     return instance_from_dict(instance, pattern, language, instance_id)


# def get_pattern_category_or_none(el) -> PatternCategory | None:
#     try:
#         return PatternCategory(el)
#     except ValueError:
#         return None


# def get_feature_vs_internal_api_or_none(el) -> FeatureVsInternalApi | None:
#     try:
#         return FeatureVsInternalApi(el)
#     except ValueError:
#         return None