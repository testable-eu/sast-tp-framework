import pytest
from unittest.mock import patch

from qualitytests.qualitytests_utils import join_resources_path

from core.exceptions import PatternDoesNotExists
from pattern_repair.utils import (
    assert_pattern_valid, compare_dicts,
    get_dict_keys, get_instance_name,
    get_files_with_ending, get_language_by_file_ending,
    list_instances_jsons, repair_keys_of_json
    )

class TestPatternRepairUtils:
    def test_assert_pattern_valid(self):
        path_to_non_existing_pattern = join_resources_path("100_non_existing")
        with pytest.raises(PatternDoesNotExists) as e_info:
            assert_pattern_valid(path_to_non_existing_pattern)
        assert "Specified Pattern `100_non_existing` does not exists." in str(e_info.value)
    
    def test_compare_dicts(self):
        o_dict = {"key1": 1, "key2": 3, "key3": 2}
        n_dict = {"key1": 1, "key3": 3, "key4": 42}
        assert {'key3': 2} == compare_dicts(o_dict, n_dict)
    
    def test_get_dict_keys(self):
        d = {
            "key1": {
                "key1.1": 0,
                "key1.2": {"key1.2.1": 0}
            },
            "key2": 42
        }
        assert set(["key1:key1.1", "key1:key1.2:key1.2.1", "key2"]) == set(get_dict_keys(d))
    
    def test_get_instance_name(self):
        path_to_pattern = join_resources_path("sample_patlib/PHP/5_pattern_to_repair")
        path_to_instance = path_to_pattern / "1_instance_5_pattern_to_repair"

        assert "1 Instance", get_instance_name(path_to_instance)
    
    def test_get_files_with_ending(self):
        path_to_pattern = join_resources_path("sample_patlib/PHP/3_global_array")
        assert [] == get_files_with_ending(path_to_pattern, ".php")
        expected_instance_1_php_file = str(path_to_pattern / "1_instance_3_global_array" / "1_instance_3_global_array.php")
        expected_instance_2_php_file = str(path_to_pattern / "2_instance_3_global_array" / "2_instance_3_global_array.php")
        assert set([expected_instance_1_php_file, expected_instance_2_php_file]) == set(get_files_with_ending(path_to_pattern, ".php", True))

    def test_get_language_by_file_ending(self):
        assert "python" == get_language_by_file_ending("test.py")
        assert "php" == get_language_by_file_ending("test.php")
        assert "javascript" == get_language_by_file_ending("test.js")
        assert "java" == get_language_by_file_ending("test.java")
        assert "scala" == get_language_by_file_ending("test.sc")
        assert "bash" == get_language_by_file_ending("test.bash")

        with pytest.raises(NotImplementedError) as e_info:
            get_language_by_file_ending("")
        assert "The ending of the given filename  is not yet supported" in str(e_info.value)
        
    def test_list_instance_jsons(self):
        path_to_pattern = join_resources_path("sample_patlib/PHP/3_global_array")
        expected_instance_1_json_file = str(path_to_pattern / "1_instance_3_global_array" / "1_instance_3_global_array.json")
        expected_instance_2_json_file = str(path_to_pattern / "2_instance_3_global_array" / "2_instance_3_global_array.json")
        assert set([expected_instance_1_json_file, expected_instance_2_json_file]) == set(list_instances_jsons(path_to_pattern))
    
    def test_repair_keys_of_json(self):
        json_dict_tested = {"a": 42, "b": {"b.0": 1}}
        json_dict_ground_truth = {"a": 42, "b": {"b.0": 1, "b.1": 1}, "c": 42, "d": 36}
        with patch("pattern_repair.utils.read_json") as read_json_mock, \
            patch("pattern_repair.utils.write_json") as write_json_mock:
            read_json_mock.side_effect = [json_dict_tested, json_dict_ground_truth]

            repair_keys_of_json("", "", ["d"])
            write_json_mock.assert_called_once_with("", {"a": 42, "b": {"b.0": 1, "b.1": ""}, "c": ""})
