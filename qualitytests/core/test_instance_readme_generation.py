import pytest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch, mock_open

from core.readme_generator import InstanceREADMEGenerator
from core.readme_markdown_elements import *
from qualitytests.qualitytests_utils import create_pattern

class TestInstanceREADMEGenerator:
    def _get_instance_readme_generator(self):
        test_pattern = create_pattern()
        instance_readme_gen = InstanceREADMEGenerator(test_pattern, None)
        instance_readme_gen.current_instance = instance_readme_gen.pattern.instances[0]
        return instance_readme_gen
    
    def test_instance_name(self):
        instance_readme_gen = self._get_instance_readme_generator()
        actual = instance_readme_gen._instance_name()
        assert isinstance(actual, list)
        assert 1 == len(actual)
        assert isinstance(actual[0], MarkdownHeading)
        assert 2 == actual[0].level
        assert "1 Instance" == actual[0].content
    
    def test_instance_description(self):
        instance_readme_gen = self._get_instance_readme_generator()
        instance_readme_gen.current_instance.description = None
        actual1 = instance_readme_gen._instance_description()
        assert [] == actual1

        instance_readme_gen.current_instance.description = "some description"
        actual2 = instance_readme_gen._instance_description()
        assert isinstance(actual2, list)
        assert 1 == len(actual2)
        assert isinstance(actual2[0], MarkdownString)

    def test_instance_code_same_source_and_sink(self):
        instance_readme_gen = self._get_instance_readme_generator()
        expected_code = instance_readme_gen.current_instance.code_path
        instance_readme_gen.current_instance.expectation_source_file = "code_file"
        instance_readme_gen.current_instance.expectation_sink_file = "code_file"
        with patch("core.readme_generator.InstanceREADMEGenerator._get_file_content_if_exists") as file_content_mock:
            file_content_mock.return_value = "x = 1"

            actual1 = instance_readme_gen._instance_code()
        file_content_mock.assert_called_once_with(expected_code)
        assert isinstance(actual1, list)
        assert 2 == len(actual1)
        assert isinstance(actual1[0], MarkdownHeading)
        assert 3 == actual1[0].level
        assert "Code" == actual1[0].content
        assert isinstance(actual1[1], MarkdownCode)

        with patch("core.readme_generator.InstanceREADMEGenerator._get_file_content_if_exists") as file_content_mock:
            file_content_mock.return_value = None

            actual2 = instance_readme_gen._instance_code()
        assert [] == actual2
    
    def test_instance_code_different_source_and_sink(self):
        instance_readme_gen = self._get_instance_readme_generator()
        expected_code = instance_readme_gen.current_instance.code_path
        instance_readme_gen.current_instance.expectation_source_file = "code_file_source"
        instance_readme_gen.current_instance.expectation_sink_file = "code_file_sink"
        with patch("core.readme_generator.InstanceREADMEGenerator._get_file_content_if_exists") as file_content_mock:
            file_content_mock.return_value = "x = 1"

            actual1 = instance_readme_gen._instance_code()
        file_content_mock.assert_called()
        assert isinstance(actual1, list)
        assert 5 == len(actual1)
        assert isinstance(actual1[0], MarkdownHeading)
        assert 3 == actual1[0].level
        assert "Code" == actual1[0].content
        assert isinstance(actual1[1], MarkdownHeading)
        assert 4 == actual1[1].level
        assert "Source File" == actual1[1].content
        assert isinstance(actual1[2], MarkdownCode)
        assert isinstance(actual1[3], MarkdownHeading)
        assert 4 == actual1[3].level
        assert "Sink File" == actual1[3].content
        assert isinstance(actual1[4], MarkdownCode)

        with patch("core.readme_generator.InstanceREADMEGenerator._get_file_content_if_exists") as file_content_mock:
            file_content_mock.reset_mock()
            file_content_mock.return_value = None

            actual2 = instance_readme_gen._instance_code()
        file_content_mock.assert_called()
        assert [] == actual2
    
    def test_instance_properties(self):
        instance_readme_gen = self._get_instance_readme_generator()
        actual = instance_readme_gen._instance_properties()
        assert isinstance(actual, list)
        assert 2 == len(actual)
        assert isinstance(actual[0], MarkdownHeading)
        assert 3 == actual[0].level
        assert "Instance Properties" == actual[0].content
        assert isinstance(actual[1], MarkdownTable)
    
    def test_instance_more(self):
        instance_readme_gen = self._get_instance_readme_generator()
        actual = instance_readme_gen._instance_more()

        assert isinstance(actual, list)
        assert 1 == len(actual)
        assert isinstance(actual[0], MarkdownCollapsible)
    
    def test_compile(self):
        instance_readme_gen = self._get_instance_readme_generator()
        with patch("core.readme_generator.InstanceREADMEGenerator._get_file_content_if_exists") as file_content_mock:
            file_content_mock.return_value = "binary"
            actual1 = instance_readme_gen._compile()

        file_content_mock.assert_called_once()
        assert isinstance(actual1, list)
        assert 1 == len(actual1)
        assert isinstance(actual1[0], MarkdownCollapsible)

        with patch("core.readme_generator.InstanceREADMEGenerator._get_file_content_if_exists") as file_content_mock:
            file_content_mock.return_value = ""
            actual2 = instance_readme_gen._compile()

        file_content_mock.assert_called_once()
        assert [] == actual2
    
    discovery_rule_example1 = """@main def main(name : String): Unit = {
        importCpg(name)
        val x1 = (name, "1_static_variables_iall", cpg.call(".*BIND_STATIC.*").location.toJson);
        println(x1)
        delete;
    } """
    discovery_rule_example2 = """@main def main(name : String): Unit = { 
        importCpg(name)
        // TODO: replace line below with your detection query
        val x2 = (name, "ID_pattern_name_i1", cpg.method.l)}; 
        println(x2)
        delete;
    } 

    
    """
    expected_discovery_rule_example1 = discovery_rule_example1.split("\n")[2].strip()
    expected_discovery_rule_example2 = "\n".join([l.strip() for l in discovery_rule_example2.split("\n")[2:4]])

    discovery_rule_testcases = [
        (discovery_rule_example1, expected_discovery_rule_example1, "./discovery_rule1.sc", "Here some description", "Here some description", MarkdownCode),
        (discovery_rule_example2, expected_discovery_rule_example2, "./discovery_rule2.sc", "", "", MarkdownCode),
        ("", "No discovery rule yet.", None, None, "", MarkdownString),
        ("print('Hello World')", "print('Hello World')", "./discovery_rule.py", "This is a python rule\n", "This is a python rule", MarkdownCode)
    ]

    @pytest.mark.parametrize("dr_return, expected_dr, rule_path, desc, expected_desc, code_or_str", discovery_rule_testcases)
    def test_discovery_rule_exists(self, dr_return, expected_dr, rule_path, desc, expected_desc, code_or_str):
        instance_readme_gen = self._get_instance_readme_generator()
        instance_readme_gen.current_instance.discovery_rule = rule_path
        instance_readme_gen.current_instance.discovery_notes = desc
        with patch("core.readme_generator.InstanceREADMEGenerator._get_file_content_if_exists") as file_content_mock:
            file_content_mock.side_effect = [desc, dr_return]
            actual = instance_readme_gen._discovery()
        file_content_mock.assert_called()
        assert isinstance(actual, list)
        assert 1 == len(actual)
        assert isinstance(actual[0], MarkdownCollapsible)
        assert isinstance(actual[0].content, list)
        assert 3 == len(actual[0].content)
        assert isinstance(actual[0].content[0], MarkdownString)
        assert expected_desc == actual[0].content[0].content
        assert isinstance(actual[0].content[1], code_or_str)
        assert expected_dr == actual[0].content[1].content
        assert isinstance(actual[0].content[2], MarkdownTable)
        assert isinstance(actual[0].heading, MarkdownHeading)
        assert "Discovery" == actual[0].heading.content
        assert 3 == actual[0].heading.level

    measurement_dict = {
                        "date": "1970-01-01 00:00:01",
                        "result": False,
                        "tool": "tool1",
                        "version": "saas",
                        "instance": "./JS/1_unset_element_array/1_instance_1_unset_element_array/1_instance_1_unset_element_array.json",
                        "pattern_id": 1,
                        "instance_id": 1,
                        "language": "JS"
                    }
    invalid_test_measurement = deepcopy(measurement_dict)
    invalid_test_measurement.pop("result")
    no_measurements_and_invalid_measurements_testcases = [
        (None, None), 
        (Path("/"), [invalid_test_measurement])
    ]

    @pytest.mark.parametrize("measurement_paths, measurement_res", no_measurements_and_invalid_measurements_testcases)
    def test_measurement_no_measurements_and_invalid_measurements(self, measurement_paths, measurement_res):
        instance_readme_gen = self._get_instance_readme_generator()
        instance_readme_gen.measurements = measurement_paths
        with patch("core.utils.list_files") as list_files_mock, \
             patch("core.utils.read_json") as read_json_mock:
            list_files_mock.return_value = ["file.json"]
            actual = instance_readme_gen._measurement()
            read_json_mock.return_value = measurement_res
        
        assert [] == actual

    
    measure_testcases = [
        ({"tool1": "maskedTool1"}, [measurement_dict]), 
        ({}, [measurement_dict]),
        ({}, [measurement_dict] + [measurement_dict])
    ]

    @pytest.mark.parametrize("mask, meas_results", measure_testcases)
    def test_measurement(self, mask, meas_results):
        instance_readme_gen = self._get_instance_readme_generator()
        instance_readme_gen.measurements = Path("/")
        instance_readme_gen.mask_dict = mask
        with patch("core.utils.list_files") as list_files_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("pathlib.Path.exists") as exist_mock:
            exist_mock.return_value = True
            list_files_mock.return_value = ["file1.json"]
            read_json_mock.return_value = meas_results

            actual = instance_readme_gen._measurement()
        
        list_files_mock.assert_called_once()
        read_json_mock.assert_called_once_with("file1.json")

        assert isinstance(actual, list)
        assert 1 == len(actual)
        assert isinstance(actual[0], MarkdownCollapsible)
        assert actual[0].is_open
        assert isinstance(actual[0].heading, MarkdownHeading)
        assert "Measurement" == actual[0].heading.content
        assert isinstance(actual[0].content, list)
        assert 1 == len(actual[0].content)
        assert isinstance(actual[0].content[0], MarkdownTable)
        if mask:
            assert "tool1" not in actual[0].content[0].to_markdown()
        else:
            assert "tool1" in actual[0].content[0].to_markdown()

    default_note =  "Can you think of a transformation, that makes this tarpit less challenging for SAST tools?"
    remediation_testcases = [
        (["", "", ""], [], []),
        (["", "", "rule"], [MarkdownString, MarkdownHeading, MarkdownString], [default_note, "Modeling Rule", "rule"]),
        (["", "transformation", ""], [MarkdownString, MarkdownHeading, MarkdownString], [default_note, "Transformation", "transformation"]),
        (["", "transformation", "rule"], [MarkdownString, MarkdownHeading, MarkdownString, MarkdownHeading, MarkdownString], [default_note, "Transformation", "transformation", "Modeling Rule", "rule"]),
        (["note", "", ""], [MarkdownString], ["note"]),
        (["note", "", "rule"], [MarkdownString, MarkdownHeading, MarkdownString], ["note", "Modeling Rule", "rule"]),
        (["note", "transformation", ""], [MarkdownString, MarkdownHeading, MarkdownString], ["note", "Transformation", "transformation"]),
        (["note", "transformation", "rule"], [MarkdownString, MarkdownHeading, MarkdownString, MarkdownHeading, MarkdownString], ["note", "Transformation", "transformation", "Modeling Rule", "rule"])
    ]

    @pytest.mark.parametrize("get_file_content_ret, expected_classes, expected_content", remediation_testcases)
    def test_remediation(self, get_file_content_ret: list, expected_classes: list, expected_content: list):
        instance_readme_gen = self._get_instance_readme_generator()
        with patch("core.readme_generator.InstanceREADMEGenerator._get_file_content_if_exists") as file_content_mock:
            file_content_mock.side_effect = get_file_content_ret

            actual = instance_readme_gen._remediation()
        
        file_content_mock.assert_called()
        if not expected_classes:
            assert [] == actual
            return
        assert isinstance(actual, list)
        assert 1 == len(actual)
        assert isinstance(actual[0], MarkdownCollapsible)
        assert isinstance(actual[0].heading, MarkdownHeading)
        assert "Remediation" == actual[0].heading.content
        assert isinstance(actual[0].content, list)
        assert len(expected_classes) == len(actual[0].content)
        assert expected_classes == [type(c) for c in actual[0].content]
        assert expected_content == [c.content for c in actual[0].content]

    get_file_content_if_exists_testcases = [
        ("description", "description", None, False),
        ("", None, None, False),
        ("", "", "", False),
        ("description in file", "file.md", "description in file", True),
        ("description in file", "file2.md", "description in file\n\n", True)
    ]

    @pytest.mark.parametrize("expected, file_path, file_content, is_file_ret", get_file_content_if_exists_testcases)
    def test_get_file_content_if_exists(self, expected: str, file_path: str, file_content: str, is_file_ret: bool):
        instance_readme_gen = self._get_instance_readme_generator()
        with patch("builtins.open", mock_open(read_data=file_content), create=True), \
            patch("pathlib.Path.is_file") as is_file_mock:
            is_file_mock.return_value = is_file_ret
            actual = instance_readme_gen._get_file_content_if_exists(file_path)
        assert expected == actual

    def test_mask(self):
        instance_readme_gen = self._get_instance_readme_generator()
        instance_readme_gen.mask_dict = {"tool2": "masked_tool2"}
        assert "tool1" == instance_readme_gen._mask("tool1")
        assert "masked_tool2" == instance_readme_gen._mask("tool2")
        instance_readme_gen.mask_dict = {}
        assert "tool2" == instance_readme_gen._mask("tool2")
