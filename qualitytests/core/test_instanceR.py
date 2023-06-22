import pytest
from pathlib import Path
from unittest.mock import patch

from core.instance import Instance
from core.exceptions import PatternDoesNotExists, InstanceInvalid
from qualitytests.qualitytests_utils import join_resources_path

class mockPattern:
    def __init__(self) -> None:
        self.pattern_id = 1

class TestInstance:
    sample_tp_lib: Path = join_resources_path("sample_patlib")

    example_instance_dict = {
        "code": {
            "path": "<code_path>",
            "injection_skeleton_broken": True
        },
        "discovery": {
            "rule": "<rule_path>",
            "method": "joern",
            "rule_accuracy": "Perfect",
            "notes": "Some notes"
        },
        "remediation": {
            "notes": "./docs/remediation_notes.md",
            "transformation": None,
            "modeling_rule": None
        },
        "compile": {
            "binary": "<bash_path>",
            "dependencies": None,
            "instruction": None
        },
        "expectation": {
            "type": "xss",
            "sink_file": "<sink_path>",
            "sink_line": 5,
            "source_file": "<source_path>",
            "source_line": 9,
            "expectation": True
        },
        "properties": {
            "category": "S0",
            "feature_vs_internal_api": "FEATURE",
            "input_sanitizer": False,
            "source_and_sink": False,
            "negative_test_case": False
        }
    }

    invalid_instances = [
        (Path("./test_instance.json"), False, {}, "The provided instance path 'test_instance.json' does not exist."),
        (Path("./1_instance_test_pattern.json"), True, {}, "Could not get id from ''."),
        (Path("./1_instance_test_pattern/1_instance_test_pattern.json"), True, {}, "Pattern 1 - Instance 1 - Please check 1_instance_test_pattern/1_instance_test_pattern.json."),
        (Path("./1_instance_test_pattern/1_instance_test_pattern.json"), True, {"name": "instance"}, "Pattern 1 - Instance 1 -  'code:path' must be contained in instance json.")
    ]

    @pytest.mark.parametrize("json_file_path, is_file_return, read_json_return, expected_error", invalid_instances)
    def test_init_invalid_instance_from_json_path(self, 
                                                json_file_path: Path,
                                                is_file_return: bool,
                                                read_json_return: dict,
                                                expected_error: str):
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch('core.utils.read_json') as read_json_mock, \
            pytest.raises(InstanceInvalid) as e_info:
            is_file_mock.return_value = is_file_return
            read_json_mock.return_value = read_json_return
            Instance.init_from_json_path(json_file_path, mockPattern())
        is_file_mock.assert_called_once()
        assert f"{expected_error} Instance is invalid." == str(e_info.value)
    
    def test_init_valid_instance_from_json_path(self):
        with patch('core.utils.read_json') as read_json_mock, \
            patch('pathlib.Path.is_file') as is_file_mock:
                    
            is_file_mock.return_value = True
            read_json_mock.return_value = TestInstance.example_instance_dict
            test_instance = Instance.init_from_json_path(Path("./1_instance_test_pattern/1_instance_test_pattern.json"), mockPattern())

        read_json_mock.assert_called_once()
        is_file_mock.assert_called_once()
        assert Path("./1_instance_test_pattern/") == test_instance.instance_path
        assert Path("./1_instance_test_pattern/1_instance_test_pattern.json") == test_instance.instance_json_path
        assert 1 == test_instance.instance_id
        assert "<code_path>" == test_instance.code_path
        assert test_instance.description is None
        assert test_instance.code_injection_skeleton_broken
        assert "xss" == test_instance.expectation_type
        assert "<sink_path>" == test_instance.expectation_sink_file
        assert 5 == test_instance.expectation_sink_line
        assert "<source_path>" == test_instance.expectation_source_file
        assert 9 == test_instance.expectation_source_line
        assert test_instance.expectation_expectation
        assert "<bash_path>" == test_instance.compile_binary
        assert test_instance.compile_instruction is None
        assert test_instance.compile_dependencies is None
        assert "<rule_path>" == test_instance.discovery_rule
        assert "joern" == test_instance.discovery_method
        assert "Perfect" == test_instance.discovery_rule_accuracy
        assert "Some notes" == test_instance.discovery_notes
        assert "S0" == test_instance.properties_category
        assert "FEATURE" == test_instance.properties_feature_vs_internal_api
        assert not test_instance.properties_input_sanitizer
        assert not test_instance.properties_source_and_sink
        assert not test_instance.properties_negative_test_case
        assert "./docs/remediation_notes.md" == test_instance.remediation_notes
        assert test_instance.remediation_transformation is None
        assert test_instance.remediation_modeling_rule is None