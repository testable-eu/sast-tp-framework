from pathlib import Path

from core import utils
from core.exceptions import InstanceInvalid

class Instance:
    @classmethod
    def init_from_json_path(cls, path_to_instance_json: Path, pattern_id: int, language: str):
        if not path_to_instance_json.is_file():
            raise InstanceInvalid(f"The provided instance path '{path_to_instance_json}' does not exist.")
        return cls._init_from_json(cls(), path_to_instance_json, pattern_id, language)
    
    def __init__(self) -> None:
        self.instance_path = None
        self.instance_json_path = None
        self.instance_id = None
        self.pattern_id = None
        self.language = None
        self.name = None
        self.pattern = None

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

    def _assert_instance(self):
        try:
            int(self.instance_id)
            assert self.language.isupper()
            assert self.instance_path.is_dir()
            assert self.instance_json_path.is_file()
            assert self.code_path.is_file()
        except Exception as e:
            raise InstanceInvalid(f"{self._log_prefix()}Instance Variables are not properly set. '{e}'")

    def _init_from_json(self, path_to_instance_json: Path, pattern_id: int, language: str):
        self.instance_path = path_to_instance_json.parent
        self.name = self.instance_path.name
        self.instance_json_path = Path(path_to_instance_json.name)
        self.language = language.upper()
        try:
            self.instance_id = utils.get_id_from_name(self.instance_path.name)
        except Exception as e:
            raise InstanceInvalid(f"Could not get id from '{self.instance_path.name}'.")
        
        self.pattern_id = pattern_id
        instance_properties = utils.read_json(self.instance_json_path)
        if not instance_properties:
            raise InstanceInvalid(f"{self._log_prefix()}Please check {self.instance_json_path}.")
        
        self.description = instance_properties.get("description", None)
        self.code_path = utils.get_path_or_none(instance_properties.get("code", {}).get("path", None))
        self.code_injection_skeleton_broken = instance_properties.get("code", {}).get("injection_skeleton_broken", None)
        self.expectation_type = instance_properties.get("expectation", {}).get("type", None)
        self.expectation_sink_file = utils.get_path_or_none(instance_properties.get("expectation", {}).get("sink_file", None))
        self.expectation_sink_line = instance_properties.get("expectation", {}).get("sink_line", None)
        self.expectation_source_file = utils.get_path_or_none(instance_properties.get("expectation", {}).get("source_file", None))
        self.expectation_source_line = instance_properties.get("expectation", {}).get("source_line", None)
        self.expectation_expectation = instance_properties.get("expectation", {}).get("expectation", None)
        self.compile_binary = utils.get_path_or_none(instance_properties.get("compile", {}).get("binary", None))
        self.compile_instruction = instance_properties.get("compile", {}).get("instruction", None)
        self.compile_dependencies = instance_properties.get("compile", {}).get("dependencies", None)
        self.discovery_rule = utils.get_path_or_none(instance_properties.get("discovery", {}).get("rule", None))
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
            attr = Path(base_path / attr).resolve()
        return attr

    def _log_prefix(self):
        return f"Pattern {self.pattern_id} - Instance {self.instance_id} - "

    def _make_path(self, path_name: str):
        return Path(self.instance_path / path_name).resolve() if path_name else None

    def __str__(self) -> str:
        return f"Instance {self.instance_id} {self.name}"

    def copy_to_tplib(self, pattern_path: Path):
        new_instance_path = pattern_path / self.instance_path.name
        new_instance_path.mkdir(parents=True, exist_ok=True)
        utils.copy_dir_content(self.instance_path, new_instance_path)
        self.instance_path = new_instance_path
        self.name = self.instance_path.name
