import pytest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch, mock_open

from core.pattern import Pattern
from core.exceptions import PatternDoesNotExists, PatternInvalid, InstanceDoesNotExists
from qualitytests.qualitytests_utils import join_resources_path, create_pattern, example_tp_dict

class TestPattern:
    sample_tp_lib: Path = join_resources_path("sample_patlib")

    example_tp_dict = {
        "name": "Test Pattern",
        "description": "./docs/description.md",
        "family": "test_pattern",
        "tags": ["sast", "language"],
        "instances": [
            "./1_instance_1_test_pattern/1_instance_1_test_pattern.json"
        ]
    }

    not_existing_patterns = [(1000, "php"), (1000, "js"), (1000, "java")]
    invalid_patterns = [
                        (3, "php", {}, "The pattern needs a valid JSON file."),
                        (3, "php", {"name": "test_instances_key_in_json_missing"}, "Pattern 3 (PHP) - Pattern JSON file needs an 'instances' key with valid relative links."),
                        (3, "php", {"instances": ["test_instances_invalid_relative_path"]}, "Pattern 3 (PHP) - The instance path 'test_instances_invalid_relative_path' is not valid.")
    ]
    valid_patterns = [
        (1, "php", example_tp_dict),
        (1, "js", example_tp_dict)
    ]

    valid_patterns_without_id = [
        (Path("path_to_json_file"), "php", Path("pattern_path"), 5),
        (Path("path_to_json_file"), "js", Path("pattern_path"), 3)
    ]

    @pytest.mark.parametrize("pattern_id, language", not_existing_patterns)
    def test_not_exising_pattern_init_from_id_and_language(self, pattern_id: int, language: str):
        with pytest.raises(PatternDoesNotExists) as e_info:
            Pattern.init_from_id_and_language(pattern_id, language, TestPattern.sample_tp_lib)
        assert f"Specified Pattern `{pattern_id}` does not exists." == str(e_info.value)

    @pytest.mark.parametrize("pattern_id, language, read_json_return, expected_assertion_error", invalid_patterns)
    def test_init_invalid_pattern_from_id_and_language(self, 
                                                       pattern_id: int, language: str,
                                                       read_json_return: dict,
                                                       expected_assertion_error: str):
        with patch('core.utils.read_json') as read_json_mock, \
            pytest.raises(PatternInvalid) as e_info:
            
            read_json_mock.return_value = read_json_return
            Pattern.init_from_id_and_language(pattern_id, language, TestPattern.sample_tp_lib)
            
        read_json_mock.assert_called_once()
        assert f"{expected_assertion_error} Pattern is invalid." == str(e_info.value)
    
    @pytest.mark.parametrize("path_to_json, language, pattern_path, expected_id", valid_patterns_without_id)
    def test_init_from_json_file_without_pattern_id(self, path_to_json: Path, language: str, pattern_path: Path, expected_id: int):
        with patch('core.utils.read_json') as read_json_mock, \
            patch('pathlib.Path.is_file') as is_file_mock, \
            patch("pathlib.Path.is_dir") as is_dir_mock, \
            patch("core.pattern.isinstance") as isinstance_mock, \
            patch('core.instance.Instance.init_from_json_path') as instance_init_mock:

            is_dir_mock.return_value = True
            is_file_mock.return_value = True
            isinstance_mock.return_value = True
            read_json_mock.return_value = TestPattern.example_tp_dict
            pattern = Pattern.init_from_json_file_without_pattern_id(path_to_json, language, pattern_path, TestPattern.sample_tp_lib)
        read_json_mock.assert_called_once()
        is_file_mock.assert_called()
        is_dir_mock.assert_called()
        isinstance_mock.assert_called()
        instance_init_mock.assert_called_once()
        assert expected_id == pattern.pattern_id
        assert path_to_json == pattern.json_path
        assert pattern_path == pattern.path
        assert language.upper() == pattern.language

    
    @pytest.mark.parametrize("pattern_id, language, read_json_return", valid_patterns)
    def test_init_valid_pattern_from_id_and_language(self, pattern_id: int, language: str,
                                                     read_json_return: dict):
        with patch('core.utils.read_json') as read_json_mock, \
            patch('pathlib.Path.is_file') as is_file_mock, \
            patch("pathlib.Path.is_dir") as is_dir_mock, \
            patch("core.pattern.isinstance") as isinstance_mock, \
            patch('core.instance.Instance.init_from_json_path') as instance_init_mock:

            is_dir_mock.return_value = True
            is_file_mock.return_value = True
            isinstance_mock.return_value = True
            read_json_mock.return_value = read_json_return
            test_pattern = Pattern.init_from_id_and_language(pattern_id, language, TestPattern.sample_tp_lib)
        
        read_json_mock.assert_called_once()
        is_file_mock.assert_called()
        is_dir_mock.assert_called()
        isinstance_mock.assert_called()
        instance_init_mock.assert_called_once()
        assert "Test Pattern" == test_pattern.name
        assert "./docs/description.md" == test_pattern.description
        assert "test_pattern" == test_pattern.family
        assert ["sast", "language"] == test_pattern.tags
    
    copy_to_tp_lib_testcases = [(1, "1_unset_element_array"), (None, "1_1_unset_element_array")]

    @pytest.mark.parametrize("ret_pattern_id, expected_name", copy_to_tp_lib_testcases)
    def test_copy_to_tp_lib(self, ret_pattern_id, expected_name):
        test_pattern = create_pattern()
        new_tplib_path = Path("/tp_lib")
        with patch("core.instance.Instance.copy_to_tplib") as copy_instance_mock, \
            patch("core.utils.copy_dir_content") as copy_dir_mock, \
            patch("core.utils.get_id_from_name") as get_id_mock:
            get_id_mock.return_value = ret_pattern_id
            test_pattern.tp_lib_path = new_tplib_path
            test_pattern.copy_to_tplib()
        copy_instance_mock.assert_called_once()
        copy_dir_mock.assert_called_once()
        expected_pattern_path = new_tplib_path / "JS" / expected_name
        assert expected_pattern_path == test_pattern.path
    
    def test_to_dict(self):
        test_pattern = create_pattern()
        with patch("core.utils.get_relative_paths") as rel_path_mock:
            rel_path_mock.return_value = None

            actual = test_pattern.to_dict()
        expected = deepcopy(example_tp_dict)
        expected["instances"] = [None]
        assert expected == actual
    
    def test_get_instance_by_id(self):
        test_pattern = create_pattern()
        instance = test_pattern.get_instance_by_id(1)
        assert test_pattern.instances[0] == instance

        with pytest.raises(InstanceDoesNotExists) as e_info:
            test_pattern.get_instance_by_id(2)
        assert "Specified Pattern Instance `2` does not exists." in str(e_info)
    
    get_description_testcases = [
        ("Some description\n", None, "Some description", False),
        ("file.md", "Some description inside a file\nTest description.   ", "Some description inside a file\nTest description.", True),
        (None, None, "", False)
    ]


    @pytest.mark.parametrize("file_path, description, expected_desc, is_file", get_description_testcases)
    def test_get_description_from_file(self, file_path, description, expected_desc, is_file):
        test_pattern = create_pattern()
        test_pattern.description = file_path
        with patch("builtins.open", mock_open(read_data=description), create=True), \
            patch("pathlib.Path.is_file") as isfile_mock:

            isfile_mock.return_value = is_file

            actual_is_file, actual = test_pattern.get_description()
        assert is_file == actual_is_file
        assert expected_desc == actual
