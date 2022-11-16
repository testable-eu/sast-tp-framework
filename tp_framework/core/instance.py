import json
from enum import Enum
from pathlib import Path
from typing import Dict

from core import utils
from core.exceptions import PatternDoesNotExists, InstanceDoesNotExists
from core.pattern import Pattern, get_pattern_path_by_pattern_id, get_pattern_by_pattern_id

import logging
from core import loggermgr

logger = logging.getLogger(loggermgr.logger_name(__name__))

class PatternCategory(str, Enum):
    S0 = "S0"
    D1 = "D1"
    D2 = "D2"
    D3 = "D3"
    D4 = "D4"


class FeatureVsInternalApi(str, Enum):
    FEATURE = "FEATURE"
    INTERNAL_API = "INTERNAL_API"


class Instance(Pattern):
    # TODO: update to current structure 09/2022
    '''
    '''

    def __init__(
            self,
            code_path: Path,
            code_injection_skeleton_broken: bool,
            compile_dependencies: Path, # added 092022
            compile_binary: Path,
            compile_instruction: str, # added 092022
            remediation_transformation: str, # added 092022
            remediation_modeling_rule: Path, # added 092022
            remediation_notes: str, # added 092022
            properties_category: PatternCategory,
            properties_negative_test_case: bool,
            properties_source_and_sink: bool,
            properties_input_sanitizer: bool,
            properties_feature_vs_internal_api: FeatureVsInternalApi,
            discovery_rule: Path,
            discovery_method: str,
            discovery_rule_accuracy: str,
            discovery_notes: str,
            expectation: bool,
            expectation_type: str,
            expectation_sink_file: Path,
            expectation_sink_line: int,
            expectation_source_file: Path,
            expectation_source_line: int,
            name: str,
            description: str,
            family: str,
            tags: list[str],
            instances: list[Path],
            language: str,
            pattern_id: int = None,
            instance_id: int = None,
            pattern_dir: Path = None,
    ) -> None:
        if pattern_id is None:
            super().__init__(name, description, family, tags, instances, language, pattern_dir=pattern_dir)
        else:
            super().__init__(name, description, family, tags, instances, language, pattern_id)

        self.code_injection_skeleton_broken = code_injection_skeleton_broken
        self.compile_dependencies = compile_dependencies # added 092022
        self.compile_binary = compile_binary
        self.compile_instruction = compile_instruction  # added 092022
        self.remediation_transformation = remediation_transformation  # added 092022
        self.remediation_modeling_rule = remediation_modeling_rule # added 092022
        self.remediation_notes = remediation_notes  # added 092022
        self.properties_category = properties_category
        self.properties_negative_test_case = properties_negative_test_case
        self.properties_source_and_sink = properties_source_and_sink
        self.properties_input_sanitizer = properties_input_sanitizer
        self.properties_feature_vs_internal_api = properties_feature_vs_internal_api
        self.expectation = expectation
        self.discovery_rule = discovery_rule
        self.discovery_method = discovery_method
        self.discovery_rule_accuracy = discovery_rule_accuracy
        self.discovery_notes = discovery_notes
        self.expectation_type = expectation_type
        self.expectation_sink_file = expectation_sink_file
        self.expectation_sink_line = expectation_sink_line
        self.expectation_source_file = expectation_source_file
        self.expectation_source_line = expectation_source_line
        self.instance_id = instance_id or self.define_instance_id(pattern_dir)
        if code_path is None:
            logger.warning("Instance without code snippet cannot even be measured by SAST tools: pattern {0}, instance {1}".format(name, instance_id))
            self.code_path = ""
        else:
            self.code_path = code_path


    def define_instance_id(self, pattern_dir: Path) -> int:
        try:
            inst_list: list[Path] = utils.list_pattern_instances_by_pattern_id(
                self.language, self.pattern_id, pattern_dir)
            id_list: list[int] = sorted(list(map(lambda x: int(str(x.name).split("_")[0]), inst_list)))
            return id_list[-1] + 1 if len(id_list) > 0 else 1
        except PatternDoesNotExists:
            return 1

    def add_instance_to_pattern_id(self, language: str, pattern_src_dir: Path, pattern_dir: Path) -> None:
        instance_dir_name: str = utils.get_instance_dir_name_from_pattern(pattern_src_dir.name, self.pattern_id,
                                                                          self.instance_id)
        pattern_dir_name: str = utils.get_pattern_dir_name_from_name(pattern_src_dir.name, self.pattern_id)
        instance_dir: Path = pattern_dir / language / pattern_dir_name / instance_dir_name
        instance_dir.mkdir(exist_ok=True, parents=True)
        instance_json_file: Path = instance_dir / f"{instance_dir_name}.json"

        with open(instance_json_file, "w") as json_file:
            instance_dict: Dict = {
                "code": {
                    "path": utils.get_relative_path_str_or_none(self.code_path),
                    "injection_skeleton_broken": self.code_injection_skeleton_broken
                },
                "remediation": {
                    "notes": self.remediation_notes,
                    "transformation": self.remediation_transformation,
                    "modeling_rule": utils.get_relative_path_str_or_none(self.remediation_modeling_rule)
                },
                "discovery": {
                    "rule": utils.get_relative_path_str_or_none(self.discovery_rule),
                    "method": self.discovery_method,
                    "rule_accuracy": self.discovery_rule_accuracy,
                    "notes": self.discovery_notes
                },
                "compile": {
                    "binary": utils.get_relative_path_str_or_none(self.compile_binary),
                    "dependencies": utils.get_relative_path_str_or_none(self.compile_dependencies),
                    "instruction": self.compile_instruction
                },
                "expectation": {
                    "type": self.expectation_type,
                    "sink_file": utils.get_relative_path_str_or_none(self.expectation_sink_file),
                    "sink_line": self.expectation_sink_line,
                    "source_file": utils.get_relative_path_str_or_none(self.expectation_source_file),
                    "source_line": self.expectation_source_line,
                    "expectation": self.expectation
                },
                "properties": {
                    "category": utils.get_enum_value_or_none(self.properties_category),
                    "feature_vs_internal_api": utils.get_enum_value_or_none(self.properties_feature_vs_internal_api),
                    "input_sanitizer": self.properties_input_sanitizer,
                    "source_and_sink": self.properties_source_and_sink,
                    "negative_test_case": self.properties_negative_test_case
                }
            }
            json.dump(instance_dict, json_file, indent=4)


# TODO: Test this
def get_instance_by_instance_id(language: str, instance_id: int, pattern_id, pattern_dir: Path) -> Instance:
    instance_dir: Path = get_instance_path_from_instance_id(language, pattern_id, instance_id, pattern_dir)
    instance_json: Path = instance_dir / f"{instance_dir.name}.json"
    with open(instance_json) as json_file:
        pattern_from_json: Dict = json.load(json_file)

    pattern, p_dir = get_pattern_by_pattern_id(language, pattern_id, pattern_dir)
    return instance_from_dict(pattern_from_json, pattern, language, pattern_id)


def get_instance_path_from_instance_id(language: str, pattern_id: int, instance_id: int, pattern_dir: Path) -> Path:
    pattern_path: Path = get_pattern_path_by_pattern_id(language, pattern_id, pattern_dir)
    filtered_res: list[str] = list(filter(
        lambda x: int(x.split("_")[0]) == instance_id,
        map(lambda y: y.name, list(pattern_path.iterdir()))
    ))
    if not filtered_res:
        raise InstanceDoesNotExists(instance_id)
    return pattern_path / filtered_res[0]


def instance_from_dict(instance_dict: Dict, pattern: Pattern, language: str, instance_id: int) -> Instance:
    return Instance(
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "code", "path")),  # code_path: Path,
        utils.get_from_dict(instance_dict, "code", "injection_skeleton_broken"),  # code_injection_skeleton_broken: bool,
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "compile", "dependencies")),  # compile_dependencies: Path, # added 092022
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "compile", "binary")),  # compile_binary: Path,
        utils.get_from_dict(instance_dict, "compile", "instruction"),  # compile_instruction: str,  # added 092022
        utils.get_from_dict(instance_dict, "remediation", "transformation"),  # remediation_transformation: str, # added 092022
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "remediation", "modeling_rule")),  # remediation_modeling_rule: Path, # added 092022
        utils.get_from_dict(instance_dict, "remediation", "notes"),  # remediation_notes: str, # added 092022
        get_pattern_category_or_none(utils.get_from_dict(instance_dict, "properties", "category")),
        utils.get_from_dict(instance_dict, "properties", "negative_test_case"),
        utils.get_from_dict(instance_dict, "properties", "source_and_sink"),
        utils.get_from_dict(instance_dict, "properties", "input_sanitizer"),
        get_feature_vs_internal_api_or_none(utils.get_from_dict(instance_dict, "properties", "feature_vs_internal_api")),
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "discovery", "rule")),
        utils.get_from_dict(instance_dict, "discovery", "method"),
        utils.get_from_dict(instance_dict, "discovery", "rule_accuracy"),
        utils.get_from_dict(instance_dict, "discovery", "notes"),
        utils.get_from_dict(instance_dict, "expectation", "expectation"),
        utils.get_from_dict(instance_dict, "expectation", "type"),
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "expectation", "sink_file")),
        utils.get_from_dict(instance_dict, "expectation", "sink_line"),
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "expectation", "source_file")),
        utils.get_from_dict(instance_dict, "expectation", "source_line"),
        pattern.name,
        pattern.description,
        pattern.family,
        pattern.tags,
        pattern.instances,
        language,
        pattern_id=pattern.pattern_id,
        instance_id=instance_id
    )


def load_instance_from_metadata(metadata: str, tp_lib: Path, language: str) -> Instance:
    metadata_path: Path = tp_lib / metadata
    if not metadata_path.exists():
        raise InstanceDoesNotExists(ref_metadata=metadata_path.name)

    with open(metadata_path) as file:
        instance: Dict = json.load(file)

    pattern_id = utils.get_id_from_name(metadata_path.parent.parent.name)
    pattern, p_dir = get_pattern_by_pattern_id(language, pattern_id, tp_lib)
    instance_id = utils.get_id_from_name(metadata_path.parent.name)
    return instance_from_dict(instance, pattern, language, instance_id)


def get_pattern_category_or_none(el) -> PatternCategory | None:
    try:
        return PatternCategory(el)
    except ValueError:
        return None


def get_feature_vs_internal_api_or_none(el) -> FeatureVsInternalApi | None:
    try:
        return FeatureVsInternalApi(el)
    except ValueError:
        return None