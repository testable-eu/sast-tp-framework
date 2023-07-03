from pathlib import Path

import pytest

import config
from core import utils
from core.exceptions import PatternDoesNotExists, TPLibDoesNotExist, LanguageTPLibDoesNotExist, DiscoveryMethodNotSupported
from unittest.mock import patch, mock_open
import qualitytests.qualitytests_utils as qualitytests_utils

def setup_three_pattern(tmp_path: Path):
    language: str = "PHP"
    tmp_tp_path: Path = tmp_path / language
    tmp_tp_path.mkdir()
    p1 = tmp_tp_path / "1_pattern_one"
    p2 = tmp_tp_path / "2_pattern_two"
    p3 = tmp_tp_path / "3_pattern_three"
    p1.mkdir()
    p2.mkdir()
    p3.mkdir()

    return language, tmp_tp_path, p1, p2, p3


class TestUtils:

    def test_check_tp_lib_1(self, tmp_path):
        with pytest.raises(TPLibDoesNotExist):
            utils.check_tp_lib(Path("wh@tever4ever"))


    def test_check_tp_lib_2(self, tmp_path):
        utils.check_tp_lib(tmp_path)


    def test_get_last_measurement_for_pattern_instance(self, tmp_path):
        m1: Path = tmp_path / "measurement-2022-03-24_10-28-00.json"
        m2: Path = tmp_path / "measurement-2022-04-10_12-25-00.json"
        m3: Path = tmp_path / "measurement-2022-04-10_18-47-00.json"
        open(m1, 'w').close()
        open(m2, 'w').close()
        open(m3, 'w').close()

        assert utils.get_last_measurement_for_pattern_instance(tmp_path) == m3


    def test_get_measurement_dir_for_language(self, tmp_path):
        MEAS = config.MEASUREMENT_REL_DIR
        language = "PHP"
        assert utils.get_measurement_dir_for_language(tmp_path, language) == tmp_path / MEAS / language


    def test_get_discovery_rule_ext(self):
        # not found
        with pytest.raises(DiscoveryMethodNotSupported):
            utils.get_discovery_rule_ext("wh@tever4ever")
        # joern
        assert ".sc" == utils.get_discovery_rule_ext("joern")


    def test_get_discovery_rules(self):
        # empty
        discovery_rule_list = []
        discovery_rule_ext = ".sc"
        assert [] == utils.get_discovery_rules(discovery_rule_list, discovery_rule_ext)
        # two different folders
        tp1 = qualitytests_utils.join_resources_path("sample_patlib") / "PHP" / "3_global_array"
        tp2 = qualitytests_utils.join_resources_path("sample_patlib") / "PHP" / "2_global_variables"
        discovery_rule_list = [tp1, tp2]
        dr_to_run = utils.get_discovery_rules(discovery_rule_list, discovery_rule_ext)
        assert len(dr_to_run) == 3
        # same folder twice
        tp1 = qualitytests_utils.join_resources_path("sample_patlib") / "PHP" / "3_global_array"
        tp2 = qualitytests_utils.join_resources_path("sample_patlib") / "PHP" / "3_global_array"
        discovery_rule_list = [tp1, tp2]
        dr_to_run = utils.get_discovery_rules(discovery_rule_list, discovery_rule_ext)
        assert len(dr_to_run) == 2
        # one upper folder
        discovery_rule_list = [qualitytests_utils.join_resources_path("sample_patlib") / "PHP"]
        dr_to_run = utils.get_discovery_rules(discovery_rule_list, discovery_rule_ext)
        assert len(dr_to_run) == 4
        # one discovery rule
        discovery_rule_list = [qualitytests_utils.join_resources_path("sample_patlib") / "PHP" / "3_global_array" / "1_instance_3_global_array" / "1_instance_3_global_array.sc"]
        dr_to_run = utils.get_discovery_rules(discovery_rule_list, discovery_rule_ext)
        assert len(dr_to_run) == 1
        # multiple discovery rules, some provided twice, some not existing
        discovery_rule_list = [
            qualitytests_utils.join_resources_path(
                "sample_patlib") / "PHP" / "3_global_array" / "1_instance_3_global_array" / "1_instance_3_global_array.sc",
            qualitytests_utils.join_resources_path(
                "sample_patlib") / "PHP" / "3_global_array" / "2_instance_3_global_array" / "2_instance_3_global_array.sc",
            qualitytests_utils.join_resources_path(
                "sample_patlib") / "PHP" / "2_global_variables" / "1_instance_2_global_variables" / "1_instance_2_global_variables.sc",
            qualitytests_utils.join_resources_path(
                "sample_patlib") / "PHP" / "3_global_array" / "1_instance_3_global_array" / "1_instance_3_global_array.sc",
            qualitytests_utils.join_resources_path(
                "sample_patlib") / "PHP" / "2_global_variables" / "1_instance_2_global_variables" / "wh@tever4ever.sc"
        ]
        dr_to_run = utils.get_discovery_rules(discovery_rule_list, discovery_rule_ext)
        assert len(dr_to_run) == 3


    def test_sast_tool_version_match(self):
        assert utils.sast_tool_version_match("1.5.3", "1.5.3")
        assert not utils.sast_tool_version_match("1.5.3", "1.5.2")
        assert utils.sast_tool_version_match("1.5.3", "1.5.3.4", nv_max=3)
        assert not utils.sast_tool_version_match("1.5.3", "1.5.3.4", nv_max=4)
        assert not utils.sast_tool_version_match("1.5.3.4", "1.5.3", nv_max=4)
        assert utils.sast_tool_version_match("1.5.3.4.5.6.", "1.5.3", nv_max=3)


    def test_get_pattern_dir_from_id(self):
        tp_lib = qualitytests_utils.join_resources_path("sample_patlib")
        assert utils.get_pattern_dir_from_id(1, "PHP", tp_lib).name == "1_static_variables"
        assert utils.get_pattern_dir_from_id(2, "PHP", tp_lib).name == "2_global_variables"
        with pytest.raises(Exception):
            utils.get_pattern_dir_from_id(99, "PHP", tp_lib)


    next_free_pattern_id_test_cases = [
        ([Path('1_instance_test_pattern'), Path('2_instance_test_pattern')], 3, 1),
        ([Path('1_instance_test_pattern'), Path('3_instance_test_pattern')], 2, 1),
        ([Path('1_instance_test_pattern'), Path('3_instance_test_pattern')], 2, 2),
    ]

    @pytest.mark.parametrize("list_dir_ret_value, expected_value, proposed_id", next_free_pattern_id_test_cases)
    def test_get_next_free_pattern_id_for_language(self, list_dir_ret_value: list, expected_value: int, proposed_id: int):
        tp_lib_path = qualitytests_utils.join_resources_path("sample_patlib")
        with patch("core.utils.list_dirs_only") as list_dir_mock:
            list_dir_mock.return_value = list_dir_ret_value
            assert expected_value == utils.get_next_free_pattern_id_for_language("PHP", tp_lib_path)
    
    get_relative_paths_testcases = [
        (Path("/tp_framework/file.sc"), Path("/tp_framework"), "./file.sc"),
        (Path("/tp_framework/file.sc"), Path("/tp_framework"), "./file.sc"),
        (Path("/file.sc"), Path("/tp_framework/PHP"), Path("/file.sc")),
    ]

    @pytest.mark.parametrize("file_path, base_path, expected", get_relative_paths_testcases)
    def test_get_relative_paths_testcases(self, file_path, base_path, expected):
        assert expected == utils.get_relative_paths(file_path, base_path)

    def test_get_id_from_name_error(self):
        with pytest.raises(ValueError):
            utils.get_id_from_name("name")

        assert 1 == utils.get_id_from_name("1_instance_85_test_pattern")
        assert 42 == utils.get_id_from_name("42_test_pattern")

    def test_get_path_or_none(self):
        assert utils.get_path_or_none("") is None
        assert utils.get_path_or_none(None) is None
        assert Path("file") == utils.get_path_or_none("file")
    
    def test_get_from_dict(self):
        assert utils.get_from_dict({}, "key1", "key2") is None
        assert utils.get_from_dict({"key1": 3}, "key1", "key2") is None
        assert utils.get_from_dict({"key1": {"key3": 3}}, "key1", "key2") is None
        assert 3 == utils.get_from_dict({"key1": {"key2": 3}}, "key1", "key2")

    get_json_file_testcases = [
        # special shortcut case to avoid warnings
        (Path("./docs"), None, None, None),
        # works as expected, only one possible JSON file
        (Path("./1_instance"), Path("instance.json"), [Path("instance.json")], None),
        # No JSON file at all
        (Path("./1_instance"), None, [], "Could not find a JSON file in 1_instance"),
        # multiple JSON files, none of them named as wanted
        (Path("./1_instance"), None, ["instance.json", "insteresting.json"], "Could not determine the right pattern JSON file. Please name it <pattern_id>_<pattern_name>.json"),     
        # multiple JSON files, but one is named correctly
        (Path("./1_instance"), Path("./1_instance/1_instance.json"), [Path("./1_instance/1_instance.json"), Path("./1_instance/interesting.json")], "Found multiple '.json' files for 1_instance"),     
    ]

    @pytest.mark.parametrize("path, expected, list_file_return, warn", get_json_file_testcases)
    def test_get_json_file(self, path, expected, list_file_return, warn):
        with patch("core.utils.logger.warning") as warn_logger, \
            patch("core.utils.list_files") as list_file_mock:
            list_file_mock.return_value = list_file_return

            actual = utils.get_json_file(path)
        
        assert expected == actual
        if warn:
            warn_logger.assert_called_with(warn)
        else:
            warn_logger.assert_not_called()

    def test_read_csv_to_dict(self):
        csv_data = """pattern_id,instance_id,instance_path,pattern_name,language,discovery_rule,successful
            1,1,<path>,<name>,JS,<discovery_rule>,no
            1,2,/some/path,Test Pattern,PHP,discovery_rule.sc,yes
            """
        expected = {
            "JS": {
                "1": {"1": "no"}
            },
            "PHP": {
                "1": {"2": "yes"}
            }
        }
        with patch("builtins.open", mock_open(read_data=csv_data), create=True):
            actual = utils.read_csv_to_dict(Path("some_path"))
        
        assert expected == actual
        with pytest.raises(Exception):
            actual["NOT_EXISTING_LANG"]
            actual["PHP"]["5"]
            actual["PHP"]["1"]["3"]
    
    def test_translate_bool(self):
        assert "YES" == utils.translate_bool(True)
        assert "NO" == utils.translate_bool(False)
