from pathlib import Path

import pytest

import config
import core.instance
import core.pattern
from core import utils
from core.exceptions import PatternDoesNotExists, TPLibDoesNotExist, LanguageTPLibDoesNotExist, DiscoveryMethodNotSupported
import qualitytests_utils

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
        path_list = utils.list_pattern_instances_by_pattern_id(language, 2, tmp_path)
        assert sorted(path_list) == sorted(path_list_expected)


    def test_list_pattern_instances_by_pattern_id_with_non_existing_pattern(self, tmp_path):
        language: str = "PHP"
        tmp_tp_path: Path = tmp_path / language
        tmp_tp_path.mkdir()

        with pytest.raises(PatternDoesNotExists):
            utils.list_pattern_instances_by_pattern_id(language, 5, tmp_path)


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
        assert [] == core.utils.get_discovery_rules(discovery_rule_list, discovery_rule_ext)
        # two different folders
        tp1 = qualitytests_utils.join_resources_path("sample_patlib") / "PHP" / "3_global_array"
        tp2 = qualitytests_utils.join_resources_path("sample_patlib") / "PHP" / "2_global_variables"
        discovery_rule_list = [tp1, tp2]
        dr_to_run = core.utils.get_discovery_rules(discovery_rule_list, discovery_rule_ext)
        assert len(dr_to_run) == 3
        # same folder twice
        tp1 = qualitytests_utils.join_resources_path("sample_patlib") / "PHP" / "3_global_array"
        tp2 = qualitytests_utils.join_resources_path("sample_patlib") / "PHP" / "3_global_array"
        discovery_rule_list = [tp1, tp2]
        dr_to_run = core.utils.get_discovery_rules(discovery_rule_list, discovery_rule_ext)
        assert len(dr_to_run) == 2
        # one upper folder
        discovery_rule_list = [qualitytests_utils.join_resources_path("sample_patlib") / "PHP"]
        dr_to_run = core.utils.get_discovery_rules(discovery_rule_list, discovery_rule_ext)
        assert len(dr_to_run) == 4
        # one discovery rule
        discovery_rule_list = [qualitytests_utils.join_resources_path("sample_patlib") / "PHP" / "3_global_array" / "1_instance_3_global_array" / "1_instance_3_global_array.sc"]
        dr_to_run = core.utils.get_discovery_rules(discovery_rule_list, discovery_rule_ext)
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
        dr_to_run = core.utils.get_discovery_rules(discovery_rule_list, discovery_rule_ext)
        assert len(dr_to_run) == 3


    # def test_get_all_nested_tuples_from_dict(self):
    #     sample_dict: Dict = {
    #         "firstLevel": {
    #             "secondLevel":
    #         }
    #     }
    #     assert False