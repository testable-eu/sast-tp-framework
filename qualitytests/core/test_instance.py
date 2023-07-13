import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from copy import deepcopy

from core.instance import Instance
from core.exceptions import InstanceInvalid
from qualitytests.qualitytests_utils import join_resources_path, create_instance, example_instance_dict


class TestInstance:
    sample_tp_lib: Path = join_resources_path("sample_patlib")

    invalid_instances = [
        (Path("./test_instance.json"), False, {}, "The provided instance path 'test_instance.json' does not exist."),
        (Path("./1_instance_test_pattern.json"), True, {}, "Could not get id from ''."),
        (Path("./1_instance_test_pattern/1_instance_test_pattern.json"), True, {}, "Pattern 1 - Instance 1 - Please check ")
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
            Instance.init_from_json_path(json_file_path, 1, "js", TestInstance.sample_tp_lib)
        is_file_mock.assert_called_once()
        assert expected_error in str(e_info.value)
    
    def test_init_valid_instance_from_json_path(self):
        with patch('core.utils.read_json') as read_json_mock, \
            patch('pathlib.Path.is_file') as is_file_mock, \
            patch("pathlib.Path.is_dir") as is_dir_mock:
                    
            is_file_mock.return_value = True
            read_json_mock.return_value = example_instance_dict
            test_instance = Instance.init_from_json_path(Path("/1_instance_test_pattern/1_instance_test_pattern.json"), 1, "js", TestInstance.sample_tp_lib)

        read_json_mock.assert_called_once()
        is_file_mock.assert_called()
        is_dir_mock.assert_called()
        assert Path("/1_instance_test_pattern/") == test_instance.path
        assert Path("/1_instance_test_pattern/1_instance_test_pattern.json") == test_instance.json_path
        assert 1 == test_instance.instance_id
        assert Path("/1_instance_test_pattern/", "<code_path>") == test_instance.code_path
        assert "Some description" == test_instance.description
        assert test_instance.code_injection_skeleton_broken
        assert "xss" == test_instance.expectation_type
        assert Path("/1_instance_test_pattern/", "<sink_path>") == test_instance.expectation_sink_file
        assert 5 == test_instance.expectation_sink_line
        assert Path("/1_instance_test_pattern/", "<source_path>") == test_instance.expectation_source_file
        assert 9 == test_instance.expectation_source_line
        assert test_instance.expectation_expectation
        assert None == test_instance.compile_binary
        assert test_instance.compile_instruction is None
        assert test_instance.compile_dependencies is None
        assert Path("/1_instance_test_pattern/", "<rule_path>") == test_instance.discovery_rule
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

    def test_copy_to_tp_lib(self):
        test_instance = create_instance()
        with patch("pathlib.Path.mkdir") as mkdir_mock, \
            patch("core.utils.copy_dir_content") as copy_mock:
            
            new_tp_lib_path = Path("/test_path")
            old_path = test_instance.path
            test_instance.copy_to_tplib(new_tp_lib_path)

        mkdir_mock.assert_called_once()
        expected_new_instance_path = new_tp_lib_path / old_path.name
        copy_mock.assert_called_once_with(old_path, expected_new_instance_path)
        assert expected_new_instance_path == test_instance.path

    def test_set_new_instance_path(self):
        test_instance = create_instance()
        new_path = Path("/test_path")
        with patch("shutil.move") as move_mock:
            test_instance.set_new_instance_path(new_path)
        move_mock.assert_called_once()
        assert new_path == test_instance.path
    
    def test_to_dict(self):
        test_instance = create_instance()
        with patch("core.utils.get_relative_paths") as rel_path_mock:
            rel_path_mock.return_value = None
            actual = test_instance.to_dict()
        path_to_instance_json = test_instance.json_path
        with open(path_to_instance_json, "r") as jfile:
            expected = json.load(jfile)
        expected["code"]["path"] = None
        expected["discovery"]["rule"] = None
        expected["compile"]["binary"] = None
        expected["expectation"]["sink_file"] = None
        expected["description"] = None
        expected["expectation"]["source_file"] = None
        assert expected == actual
    
    def test_get_description_from_file(self):
        test_pattern = create_instance()
        test_pattern.description = "file.md"
        expected_description = "Some description in a file\nTest description.\n\n"
        with patch("builtins.open", mock_open(read_data=expected_description), create=True), \
            patch("pathlib.Path.is_file") as isfile_mock:

            isfile_mock.return_value = True

            is_file, actual = test_pattern.get_description()
        assert is_file
        assert expected_description.strip() == actual

    def test_get_description_(self):
        test_pattern = create_instance()
        expected_description = "Some description in a file\nTest description."
        test_pattern.description = expected_description
        with patch("pathlib.Path.is_file") as isfile_mock:
            isfile_mock.return_value = False

            is_file, actual = test_pattern.get_description()
        assert not is_file
        assert expected_description.strip() == actual
    
    path_properties_testcases = [
        (Path("/test")), Path("../tplib"), Path("/tpframework/tplib")
    ]

    @pytest.mark.parametrize("new_path", path_properties_testcases)
    def test_path_properties_are_relative_and_resolve_to_path_when_called(self, new_path: Path):
        test_instance = create_instance()
        test_instance.json_path = Path("./my_awesome_json.json")
        test_instance.code_path = Path("./awesome_js_code.js")
        test_instance.expectation_sink_file = Path("./awesome_js_code.js")
        test_instance.expectation_source_file = Path("./awesome_js_code.js")
        test_instance.compile_binary = None
        test_instance.discovery_rule = Path("../test_scala.sc")

        test_instance.path = new_path
        assert Path(new_path / "my_awesome_json.json").resolve() == test_instance.json_path
        assert Path(new_path / "awesome_js_code.js").resolve() == test_instance.code_path
        assert Path(new_path / "awesome_js_code.js").resolve() == test_instance.expectation_sink_file
        assert Path(new_path / "awesome_js_code.js").resolve() == test_instance.expectation_source_file
        assert test_instance.compile_binary is None
        assert Path(new_path / "../test_scala.sc").resolve() == test_instance.discovery_rule
    
    def test_instance_deepcopy(self):
        test_instance = create_instance()
        test_instance.code_path = Path("./a.php")
        copied_instance = deepcopy(test_instance)
        copied_instance.path = Path("/tmp")
        copied_instance.language = "new_language"
        assert copied_instance.path != test_instance.path
        assert copied_instance.code_path.relative_to(copied_instance.path) == test_instance.code_path.relative_to(test_instance.path)
        assert copied_instance.language != test_instance.language
