from pathlib import Path

import pytest

import config
from core import utils
from core.exceptions import PatternDoesNotExists, TPLibDoesNotExist, LanguageTPLibDoesNotExist, DiscoveryMethodNotSupported
from unittest.mock import patch
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


    def test_list_pattern_paths_for_language(self, tmp_path):
        language, tmp_tp_path, p1, p2, p3 = setup_three_pattern(tmp_path)
        path_list_expected = [p1, p2, p3]

        path_list = utils.list_pattern_paths_for_language(language, tmp_path)
        assert sorted(path_list) == sorted(path_list_expected)


    def test_list_pattern_paths_for_language_void_dir(self, tmp_path):
        language: str = "PHP"
        tmp_tp_path: Path = tmp_path / language
        tmp_tp_path.mkdir()

        path_list_expected = []

        path_list = utils.list_pattern_paths_for_language(language, tmp_path)
        assert sorted(path_list) == sorted(path_list_expected)


    def test_list_pattern_paths_for_non_existing_language(self, tmp_path):
        language: str = "PHP"
        with pytest.raises(LanguageTPLibDoesNotExist):
            utils.list_pattern_paths_for_language(language, tmp_path)


    # TODO: to be fixed, misses the json file
    @pytest.mark.skip()
    def test_list_pattern_instances_by_pattern_id(self, tmp_path):
        language, tmp_tp_path, p1, p2, p3 = setup_three_pattern(tmp_path)

        pi1 = p2 / ("1_instance_" + p2.name)
        pi2 = p2 / ("2_instance_" + p2.name)
        pi3 = p2 / ("3_instance_" + p2.name)
        pi1.mkdir()
        pi2.mkdir()
        pi3.mkdir()

        path_list_expected = [pi1, pi2, pi3]
        path_list = utils.list_tpi_paths_by_tp_id(language, 2, tmp_path)
        assert sorted(path_list) == sorted(path_list_expected)


    def test_list_pattern_instances_by_pattern_id_with_non_existing_pattern(self, tmp_path):
        language: str = "PHP"
        tmp_tp_path: Path = tmp_path / language
        tmp_tp_path.mkdir()

        with pytest.raises(PatternDoesNotExists):
            utils.list_tpi_paths_by_tp_id(language, 5, tmp_path)


    # TODO: to be fixed
    @pytest.mark.skip()
    def test_get_or_create_tp_lib_for_lang_existing_folder(self, tmp_path):
        language: str = "PHP"
        path_tp_language_exp = tmp_path / language
        path_tp_language_exp.mkdir()
        path_tp_language_act = utils.get_or_create_language_dir(language, tmp_path)
        assert path_tp_language_exp.is_dir() == path_tp_language_act.is_dir()


    def test_get_or_create_pattern_dir_existing_lang_dir(self, tmp_path):
        language, tmp_tp_path, p1, p2, p3 = setup_three_pattern(tmp_path)
        path_pattern_exp = tmp_tp_path / "4_pattern_four"
        path_pattern_act = utils.get_or_create_pattern_dir(language, 4, "Pattern Four", tmp_path)
        assert path_pattern_exp.is_dir() == path_pattern_act.is_dir()


    def test_get_or_create_pattern_dir_non_existing_lang_dir(self, tmp_path):
        language: str = "PHP"
        tmp_tp_path: Path = tmp_path / language
        path_pattern_exp = tmp_tp_path / "1_pattern_one"
        path_pattern_act = utils.get_or_create_pattern_dir(language, 1, "Pattern One", tmp_path)
        assert path_pattern_exp.is_dir() == path_pattern_act.is_dir()


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


    def test_get_instance_dir_from_id(self):
        tp_path = qualitytests_utils.join_resources_path("sample_patlib") / "PHP" / "3_global_array"
        assert utils.get_instance_dir_from_id(1, tp_path).name == "1_instance_3_global_array"
        assert utils.get_instance_dir_from_id(2, tp_path).name == "2_instance_3_global_array"
        with pytest.raises(Exception):
            utils.get_instance_dir_from_id(3, tp_path)


    def test_get_tpi_id_from_jsonpath(self):
        jp = qualitytests_utils.join_resources_path(
            "sample_patlib") / "PHP" / "3_global_array" / "1_instance_3_global_array" / "1_instance_3_global_array.json"
        assert utils.get_tpi_id_from_jsonpath(jp) == 1
        jp = qualitytests_utils.join_resources_path(
            "sample_patlib") / "PHP" / "3_global_array" / "1_instance_3_global_array" / "111_instance_3_global_array.json"
        assert utils.get_tpi_id_from_jsonpath(jp) == 1
        jp = qualitytests_utils.join_resources_path(
            "sample_patlib") / "PHP" / "3_global_array" / "2_instance_3_global_array" / "111_instance_3_global_array.json"
        assert utils.get_tpi_id_from_jsonpath(jp) == 2

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