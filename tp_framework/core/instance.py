import shutil
import subprocess
from pathlib import Path
from typing import Tuple

from core import utils
from core.exceptions import InstanceInvalid
from core.instance_repair import InstanceRepair


# class PatternCategory(str, Enum):
#     S0 = "S0"
#     D1 = "D1"
#     D2 = "D2"
#     D3 = "D3"
#     D4 = "D4"


# class FeatureVsInternalApi(str, Enum):
#     FEATURE = "FEATURE"
#     INTERNAL_API = "INTERNAL_API"

class Instance:
    @classmethod
    def init_from_json_path(cls, path_to_instance_json: Path, 
                            pattern_id: int, language: str, tp_lib_path: Path):
        if not path_to_instance_json.is_file():
            raise InstanceInvalid(f"The provided instance path '{path_to_instance_json}' does not exist.")
        return cls._init_from_json(cls(), path_to_instance_json, pattern_id, language, tp_lib_path)
    
    def __init__(self) -> None:
        self.path = None
        self.json_path = None
        self.instance_id = None
        self.pattern_id = None
        self.language = None
        self.name = None
        self.tp_lib_path = None

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
            assert self.path.is_dir()
            assert self.json_path.is_file()
        except Exception as e:
            raise InstanceInvalid(f"{self._log_prefix()}Instance Variables are not properly set. '{e}'")

    def _init_from_json(self, path_to_instance_json: Path, pattern_id: int, language: str, tp_lib_path: Path):
        self.path = path_to_instance_json.parent
        self.name = self.path.name
        self.json_path = Path(path_to_instance_json.name)
        self.language = language.upper()
        self.tp_lib_path = tp_lib_path
        try:
            self.instance_id = utils.get_id_from_name(self.path.name)
        except Exception as e:
            raise InstanceInvalid(f"Could not get id from '{self.path.name}'.")
        self.pattern_id = pattern_id
        instance_properties = utils.read_json(self.json_path)
        if not instance_properties:
            raise InstanceInvalid(f"{self._log_prefix()}Please check {self.json_path}.")
        
        self.description = instance_properties.get("description", None)
        self.code_path = utils.get_path_or_none(utils.get_from_dict(instance_properties, "code", "path"))
        self.code_injection_skeleton_broken = utils.get_from_dict(instance_properties, "code", "injection_skeleton_broken")
        self.expectation_type = utils.get_from_dict(instance_properties, "expectation", "type")
        self.expectation_sink_file = utils.get_path_or_none(utils.get_from_dict(instance_properties, "expectation", "sink_file"))
        self.expectation_sink_line = utils.get_from_dict(instance_properties, "expectation", "sink_line")
        self.expectation_source_file = utils.get_path_or_none(utils.get_from_dict(instance_properties, "expectation", "source_file"))
        self.expectation_source_line = utils.get_from_dict(instance_properties, "expectation", "source_line")
        self.expectation_expectation = utils.get_from_dict(instance_properties, "expectation", "expectation")
        self.compile_binary = utils.get_path_or_none(utils.get_from_dict(instance_properties, "compile", "binary"))
        self.compile_instruction = utils.get_from_dict(instance_properties, "compile", "instruction")
        self.compile_dependencies = utils.get_from_dict(instance_properties, "compile", "dependencies")
        self.discovery_rule = utils.get_path_or_none(utils.get_from_dict(instance_properties, "discovery", "rule"))
        self.discovery_method = utils.get_from_dict(instance_properties, "discovery", "method")
        self.discovery_rule_accuracy = utils.get_from_dict(instance_properties, "discovery", "rule_accuracy")
        self.discovery_notes = utils.get_from_dict(instance_properties, "discovery", "notes")
        self.properties_category = utils.get_from_dict(instance_properties, "properties", "category")
        self.properties_feature_vs_internal_api = utils.get_from_dict(instance_properties, "properties", "feature_vs_internal_api")
        self.properties_input_sanitizer = utils.get_from_dict(instance_properties, "properties", "input_sanitizer")
        self.properties_source_and_sink = utils.get_from_dict(instance_properties, "properties", "source_and_sink")
        self.properties_negative_test_case = utils.get_from_dict(instance_properties, "properties", "negative_test_case")
        self.remediation_notes = utils.get_from_dict(instance_properties, "remediation", "notes")
        self.remediation_transformation = utils.get_from_dict(instance_properties, "remediation", "transformation")
        self.remediation_modeling_rule = utils.get_from_dict(instance_properties, "remediation", "modeling_rule")
        self._assert_instance()
        return self

    def __deepcopy__(self, memo):
        copied_instance = Instance()
        for key, value in vars(self).items():
            copied_instance.__setattr__(key, value)
        return copied_instance

    def __getattribute__(self, name):
        base_path = super().__getattribute__("path")
        attr = super().__getattribute__(name)
        if isinstance(attr, Path) and attr != base_path:
            attr = Path(base_path / attr).resolve()
        return attr
    
    def __str__(self) -> str:
        return f"{self.language} - p{self.pattern_id}:{self.instance_id}"
    
    def __repr__(self) -> str:
        return f"{self.pattern_id}_i{self.instance_id}"

    def _log_prefix(self):
        return f"Pattern {self.pattern_id} - Instance {self.instance_id} - "

    def copy_to_tplib(self, pattern_path: Path):
        new_instance_path = pattern_path / self.path.name
        new_instance_path.mkdir(parents=True, exist_ok=True)
        utils.copy_dir_content(self.path, new_instance_path)
        self.path = new_instance_path
        self.name = self.path.name
    
    # same function as in Pattern, could use some interface for that, or move to utils?
    def get_description(self) -> Tuple[bool, str]:
        if self.description and " " not in self.description and Path(self.path / self.description).resolve().is_file():
            with open(Path(self.path / self.description).resolve(), "r") as desc_file:
                return True, "".join(desc_file.readlines()).strip()
        else:
            return False, self.description.strip() if self.description else ""

    def set_new_instance_path(self, new_path):
        old_path = self.path
        self.path = new_path
        shutil.move(old_path, self.path)

    def repair(self, pattern):
        InstanceRepair(self, pattern).repair()
    
    def to_dict(self):
        return {
                "description": self.description,
                "code": {
                    "path": utils.get_relative_paths(self.code_path, self.path),
                    "injection_skeleton_broken": self.code_injection_skeleton_broken
                },
                "discovery": {
                    "rule": utils.get_relative_paths(self.discovery_rule, self.path),
                    "method": self.discovery_method,
                    "rule_accuracy": self.discovery_rule_accuracy,
                    "notes": self.discovery_notes
                },
                "compile": {
                    "binary": utils.get_relative_paths(self.compile_binary, self.path),
                    "instruction": self.compile_instruction,
                    "dependencies": self.compile_dependencies
                },
                "expectation": {
                    "type": self.expectation_type,
                    "sink_file": utils.get_relative_paths(self.expectation_sink_file, self.path),
                    "sink_line": self.expectation_sink_line,
                    "source_file": utils.get_relative_paths(self.expectation_source_file, self.path),
                    "source_line": self.expectation_source_line,
                    "expectation": self.expectation_expectation
                },
                "properties": {
                    "category": self.properties_category,
                    "feature_vs_internal_api": self.properties_feature_vs_internal_api,
                    "input_sanitizer": self.properties_input_sanitizer,
                    "source_and_sink": self.properties_source_and_sink,
                    "negative_test_case": self.properties_negative_test_case
                },
                "remediation": {
                    "notes": self.remediation_notes,
                    "transformation": self.remediation_transformation,
                    "modeling_rule": self.remediation_modeling_rule
                }
            }

    def validate_for_discovery(self):
        ############## TMP ##############
        if self.pattern_id == 47 and self.instance_id == 1:
            return False
        if self.pattern_id == 48 and self.instance_id == 1:
            return False
        if self.pattern_id == 55 and self.instance_id == 1:
            return False
        if self.pattern_id == 80 and self.instance_id == 2:
            return False
        if self.pattern_id == 83 and self.instance_id == 3:
            return False
        return True
        #################################

        if not self.discovery_rule or not self.discovery_method:
            return False
        if self.discovery_method and self.discovery_rule.suffix != utils.get_discovery_rule_ext(self.discovery_method):
            return False
        test_bin = Path(__file__).parent  / "cpg_Test.bin"
        try:
            cmd = f"joern --script {self.discovery_rule} --params name={test_bin.resolve()} 2>&1"
            output = subprocess.check_output(cmd, shell=True).decode('utf-8-sig')
        except subprocess.CalledProcessError:
            return False
        except:
            return False
        return True
