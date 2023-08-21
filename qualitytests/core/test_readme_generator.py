import pytest
from pathlib import Path
from unittest.mock import patch

from core.repair.readme_generator import READMEGenerator
from core.repair.readme_markdown_elements import *
from qualitytests.qualitytests_utils import create_pattern, join_resources_path

class TestREADMEGenerator:

    def _get_readme_generator(self):
        test_pattern = create_pattern()
        with patch("pathlib.Path.is_dir") as is_dir_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("core.utils.read_csv_to_dict") as csv_to_dict_mock:
            is_dir_mock.return_value = True
            read_json_mock.return_value = {}
            csv_to_dict_mock.return_value = {"JS": {"1": {"1": "yes"}}}

            readme_generator = READMEGenerator(test_pattern, "discovery.csv", Path("dont_care"), "mask.json")
        
        is_dir_mock.assert_called_once()
        read_json_mock.assert_called_once()
        csv_to_dict_mock.assert_called_once()
        return readme_generator


    init_readme_generator_testcases = [
        # everyting alright
        ("discovery.csv", {"JS": {"1": {"1": True}}}, True, "mask.json", None),
        # Language "JS" not in discovery dict
        ("discovery.csv", {"AWESOME": {"1": {"1": True}}}, True, "mask.json", "Generating README for JS - p1: Cannot find discovery rule results for language JS"),
        # discovery dict of language is not of type dict
        ("discovery.csv", {"JS": None}, True, "mask.json", "Generating README for JS - p1: Cannot find discovery rule results for language JS"),
        # no measurement results
        ("discovery.csv", {"JS": {"1": {"1": True}}}, False, "mask.json", "Generating README for JS - p1: Cannot locate `measurement_results` in 'dont_care'"),
    ]

    @pytest.mark.parametrize("dr_file, dr_res, is_dir, mask_file, warn", init_readme_generator_testcases)
    def test_init_readme_generator_discovery_results(self, dr_file, dr_res, is_dir, mask_file, warn):
        test_pattern = create_pattern()
        with patch("pathlib.Path.is_dir") as is_dir_mock, \
            patch("core.repair.readme_generator.logger.warning") as warn_logger, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("core.utils.read_csv_to_dict") as csv_to_dict_mock:
            is_dir_mock.return_value = is_dir
            csv_to_dict_mock.return_value = dr_res

            readme_generator = READMEGenerator(test_pattern, dr_file, Path("dont_care"), mask_file)
        
        is_dir_mock.assert_called_once()
        csv_to_dict_mock.assert_called_once_with(dr_file)
        if warn:
            warn_logger.assert_called_once_with(warn)
        else:
            warn_logger.assert_not_called()

        read_json_mock.assert_called_once_with(mask_file)
        assert read_json_mock.return_value == readme_generator.mask
    
    def test_comment(self):
        test_readme_gen = self._get_readme_generator()
        actual = test_readme_gen._comment()
        assert isinstance(actual, list)
        assert 1 == len(actual)
        assert isinstance(actual[0], MarkdownComment)
    
    def test_heading(self):
        test_readme_gen = self._get_readme_generator()
        actual = test_readme_gen._heading()
        assert isinstance(actual, list)
        assert 1 == len(actual)
        assert isinstance(actual[0], MarkdownHeading)
        assert 1 == actual[0].level
        assert "Test Pattern" == actual[0].content
    
    def test_description(self):
        test_readme_gen = self._get_readme_generator()
        with patch("core.pattern.Pattern.get_description") as get_description_mock:
            get_description_mock.return_value = (True, "test")
            actual = test_readme_gen._pattern_description()
        get_description_mock.assert_called_once()
        assert isinstance(actual, list)
        assert 2 == len(actual)
        assert isinstance(actual[0], MarkdownHeading)
        assert 2 == actual[0].level
        assert "Description" == actual[0].content
        assert isinstance(actual[1], MarkdownString)
        assert "test" == actual[1].content
    
    def test_tags(self):
        test_readme_gen = self._get_readme_generator()
        actual = test_readme_gen._tags()
        assert isinstance(actual, list)
        assert 2 == len(actual)
        assert isinstance(actual[0], MarkdownString)
        assert "Tags" in actual[0].content
        assert isinstance(actual[1], MarkdownString)
        assert "Version" in actual[1].content
    
    def test_pattern_metadata_including_discovery_rule_results(self):
        test_readme_gen = self._get_readme_generator()
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.utils.translate_bool") as translate_bool_mock:
            actual = test_readme_gen._pattern_metadata()       
        assert isinstance(actual, list)
        assert 2 == len(actual)
        assert isinstance(actual[0], MarkdownHeading)
        assert 2 == actual[0].level
        assert "Overview" == actual[0].content
        assert isinstance(actual[1], MarkdownTable)
        assert "rule successfull" in actual[1].to_markdown()
    
    def test_pattern_metadata_without_discovery_rule_results(self):
        test_readme_gen = self._get_readme_generator()
        test_readme_gen.discovery_rule_results = None
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.utils.translate_bool") as translate_bool_mock:
            actual = test_readme_gen._pattern_metadata()       
        assert isinstance(actual, list)
        assert 2 == len(actual)
        assert isinstance(actual[0], MarkdownHeading)
        assert 2 == actual[0].level
        assert "Overview" == actual[0].content
        assert isinstance(actual[1], MarkdownTable)
        assert "rule successfull" not in actual[1].to_markdown()
    
    def test_instances(self):
        test_readme_gen = self._get_readme_generator()
        with patch("core.repair.readme_generator.InstanceREADMEGenerator.generate_md") as generate_md_mock:
            actual = test_readme_gen._instances()
        generate_md_mock.assert_called_once()
        assert generate_md_mock.return_value == actual
    
    def test_generate_readme(self):
        # Could actually assert the complete readme.
        # at the moment only assert, that the function works in general
        test_readme_gen = self._get_readme_generator()
        test_readme_gen.measurement_results = None
        test_readme_gen.generate_README()
    
    # integration test
    def test_generate_complete_readme(self):
        from core.pattern import Pattern
        from core.measurement import Measurement
        sample_tp_lib = join_resources_path("sample_patlib")
        test_pattern = Pattern.init_from_id_and_language(1, "php", sample_tp_lib)
        
        with patch("pathlib.Path.is_dir") as is_dir_mock, \
            patch("core.utils.read_json") as mask_json_mock, \
            patch("core.utils.read_csv_to_dict") as discovery_rule_results:
            is_dir_mock.return_value = True
            mask_json_mock.return_value = {"tool1": "masked_tool"}
            discovery_rule_results.return_value = {"PHP": {"1": {"1": "yes", "2": "no"}}}

            readme_generator = READMEGenerator(test_pattern, "discovery.csv", Path("dont_care"), "mask.json")
        
        is_dir_mock.assert_called_once()
        mask_json_mock.assert_called_once()
        discovery_rule_results.assert_called_once()

        measurement1 = Measurement("1970-01-01 00:00:01", False, False, "tool1", "saas")
        measurement2 = Measurement("1970-01-01 00:00:01", False, True, "tool2", "v2")
        measurement3 = Measurement("2023-01-01 00:00:01", True, False, "tool1", "saas")
        measurement4 = Measurement("2023-01-01 00:00:01", True, True, "tool2", "v2")

        with patch("core.utils.list_files") as list_files_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("core.measurement.Measurement.init_from_measurement_dict") as measurement_mock, \
            patch("pathlib.Path.exists") as path_exist_mock:
            list_files_mock.return_value = ["file1.md", "file2.md"]
            path_exist_mock.return_value = True
            measurement_mock.side_effect = [measurement1, measurement2, measurement3, measurement4]
            read_json_mock.return_value = [{}, {}]

            actual = readme_generator.generate_README()

        path_exist_mock.assert_called_once()
        path_to_expected_readme = sample_tp_lib / "PHP" / "1_static_variables" / "README.md"
        with open(path_to_expected_readme, "r") as fp:
            expected = fp.read()
        with open("tmp.md", "w") as f:
            f.write(actual)

        assert expected == actual
