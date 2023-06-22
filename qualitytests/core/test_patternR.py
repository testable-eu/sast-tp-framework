import pytest
from pathlib import Path
from unittest.mock import patch

from core.pattern import Pattern
from core.exceptions import PatternDoesNotExists, PatternInvalid
from qualitytests.qualitytests_utils import join_resources_path

class TestPatternR:
    sample_tp_lib: Path = join_resources_path("sample_patlib")

    example_pattern_dict = {
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
        (1, "php", example_pattern_dict),
        (1, "js", example_pattern_dict)
    ]

    valid_patterns_without_id = [
        (Path("path_to_json_file"), "php", Path("pattern_path"), 5),
        (Path("path_to_json_file"), "js", Path("pattern_path"), 3)
    ]

    @pytest.mark.parametrize("pattern_id, language", not_existing_patterns)
    def test_not_exising_pattern_init_from_id_and_language(self, pattern_id: int, language: str):
        with pytest.raises(PatternDoesNotExists) as e_info:
            Pattern.init_from_id_and_language(pattern_id, language, TestPatternR.sample_tp_lib)
        assert f"Specified Pattern `{pattern_id}` does not exists." == str(e_info.value)

    @pytest.mark.parametrize("pattern_id, language, read_json_return, expected_assertion_error", invalid_patterns)
    def test_init_invalid_pattern_from_id_and_language(self, 
                                                       pattern_id: int, language: str,
                                                       read_json_return: dict,
                                                       expected_assertion_error: str):
        with patch('core.utils.read_json') as read_json_mock, \
            pytest.raises(PatternInvalid) as e_info:
            
            read_json_mock.return_value = read_json_return
            Pattern.init_from_id_and_language(pattern_id, language, TestPatternR.sample_tp_lib)
            
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
            read_json_mock.return_value = TestPatternR.example_pattern_dict
            pattern = Pattern.init_from_json_file_without_pattern_id(path_to_json, language, pattern_path, TestPatternR.sample_tp_lib)
        read_json_mock.assert_called_once()
        is_file_mock.assert_called()
        is_dir_mock.assert_called()
        isinstance_mock.assert_called()
        instance_init_mock.assert_called_once()
        assert expected_id == pattern.pattern_id
        assert path_to_json == pattern.pattern_json_path
        assert pattern_path == pattern.pattern_path
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
            test_pattern = Pattern.init_from_id_and_language(pattern_id, language, TestPatternR.sample_tp_lib)
        
        read_json_mock.assert_called_once()
        is_file_mock.assert_called()
        is_dir_mock.assert_called()
        isinstance_mock.assert_called()
        instance_init_mock.assert_called_once()
        assert "Test Pattern" == test_pattern.name
        assert "./docs/description.md" == test_pattern.description
        assert "test_pattern" == test_pattern.family
        assert ["sast", "language"] == test_pattern.tags