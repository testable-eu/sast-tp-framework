from pathlib import Path
from typing import Dict
from unittest.mock import patch, call
import json
import sys

import pytest

pytest_plugins = ('pytest_asyncio',)

from cli import interface
from core.errors import measurementNotFound
from core.exceptions import DiscoveryRuleParsingResultError

from qualitytests.qualitytests_utils import join_resources_path, create_mock_cpg, \
    get_result_output_dir, get_logfile_path, in_logfile, init_measure_test, \
    init_sastreport_test, init_test, create_pattern


class TestInterface:


    def _init_discovery_test(self, tmp_path, mocker):
        init = {}
        init["src_dir"] = tmp_path
        init["language"] = "PHP"
        init["tool1"] = {"name": "dummyTool", "version": "1"}
        init["tool2"] = {"name": "dummyTool", "version": "2"}
        init["tool3"] = {"name": "anotherDummyTool", "version": "1.2"}
        init["tp_lib_path"] = join_resources_path("sample_patlib")
        mocked_tool_interface: Dict = {
            "supported_languages": ["PHP"],
            "tool_interface": "qualitytests.core.sast_test.SastTest"
        }
        mocker.patch("sast.utils.load_sast_specific_config", return_value=mocked_tool_interface)
        mocker.patch("core.discovery.run_generate_cpg_cmd",
                     return_value="Done",
                     side_effect=create_mock_cpg(tmp_path / "cpg_binary.bin"))
        mocker.patch("core.discovery.run_joern_scala_query_for_test",
                     return_value="Done")
        with open(join_resources_path("sample_joern") / "joern_discovery_query_res.json", "r") as data_file:
            joern_res = json.load(data_file)
        exp_discovery_rule_results = (
            join_resources_path("sample_joern") / "binary.bin",
            "1_static_variables_iall",
            joern_res
        )
        mocker.patch("core.discovery.run_joern_discovery_rule", return_value=exp_discovery_rule_results)
        return init


    def test_run_discovery_for_pattern_list_1(self, tmp_path, capsys, mocker):
        init = self._init_discovery_test(tmp_path, mocker)
        itools: list[Dict] = [
            init["tool1"]
        ]
        # Test 1: two patterns with measurements
        pattern_id_list: list[int] = [1, 2]
        interface.run_discovery_for_pattern_list(init["src_dir"], pattern_id_list, init["language"], itools,
                                                 tp_lib_path=init["tp_lib_path"])
        out = capsys.readouterr().out
        captured_out_lines = out.split("\n")
        sys.stdout.write(out)
        output_dir = get_result_output_dir(captured_out_lines)
        assert (output_dir and output_dir.is_dir() and output_dir.iterdir())


    def test_run_discovery_for_pattern_list_2(self, tmp_path, capsys, mocker):
        init = self._init_discovery_test(tmp_path, mocker)
        itools: list[Dict] = [
            init["tool1"]
        ]
        # Test 2: three patterns, one no measurements
        pattern_id_list: list[int] = [1, 2, 3]
        interface.run_discovery_for_pattern_list(init["src_dir"], pattern_id_list, init["language"], itools,
                                                 tp_lib_path=init["tp_lib_path"])
        out = capsys.readouterr().out
        captured_out_lines = out.split("\n")
        sys.stdout.write(out)
        output_dir = get_result_output_dir(captured_out_lines)
        assert (output_dir and output_dir.is_dir() and output_dir.iterdir())
        logfile = get_logfile_path(captured_out_lines)
        assert logfile and in_logfile(logfile, measurementNotFound(3), lastNlines=2)


    def test_run_discovery_for_pattern_list_3(self, tmp_path, capsys, mocker):
        init = self._init_discovery_test(tmp_path, mocker)
        itools: list[Dict] = [
            init["tool1"]
        ]
        # Test 3: two patterns with measurements, different output dir
        pattern_id_list: list[int] = [1, 2]
        ioutput_dir = join_resources_path("../temp").resolve()
        ioutput_dir.mkdir(parents=True, exist_ok=True)
        interface.run_discovery_for_pattern_list(init["src_dir"], pattern_id_list, init["language"], itools,
                                                 tp_lib_path=init["tp_lib_path"], output_dir=ioutput_dir)
        out = capsys.readouterr().out
        captured_out_lines = out.split("\n")
        sys.stdout.write(out)
        output_dir = get_result_output_dir(captured_out_lines)
        assert (output_dir and ioutput_dir == output_dir.parent and output_dir.iterdir())
        logfile = get_logfile_path(captured_out_lines)
        assert logfile and logfile.is_file()


    def test_manual_discovery(self, tmp_path, capsys, mocker):
        init = self._init_discovery_test(tmp_path, mocker)
        src_dir: Path = tmp_path
        discovery_method = "joern"
        discovery_rule_list = [
            join_resources_path("sample_patlib/JS"),
            join_resources_path("sample_patlib/PHP/1_static_variables"),
            join_resources_path("sample_patlib/whatever"),
            join_resources_path("sample_patlib/PHP/2_static_variables"),
            "Whatever we want to put here that is not a proper folder :) \ $#$@!^&*()=+[]{}~`/",
            join_resources_path("sample_patlib/PHP/3_global_array/1_instance_3_global_array/1_instance_3_global_array.sc")
        ]
        language = "PHP"
        ioutput_dir = join_resources_path("../temp").resolve()
        ioutput_dir.mkdir(parents=True, exist_ok=True)
        interface.manual_discovery(src_dir, discovery_method, discovery_rule_list, language,
                                   timeout_sec=0, output_dir=ioutput_dir)
        out = capsys.readouterr().out
        captured_out_lines = out.split("\n")
        sys.stdout.write(out)
        output_dir = get_result_output_dir(captured_out_lines)
        assert (output_dir and ioutput_dir == output_dir.parent and output_dir.iterdir())
        logfile = get_logfile_path(captured_out_lines)
        assert logfile and logfile.is_file()


    # @pytest.mark.asyncio
    # async def test_sast_measurement(self, tmp_path, capsys, mocker):
    #     init = {}
    #     init_measure_test(init, mocker)
    #     await interface.measure_list_patterns(init["patterns"], init["language"], tools=init["tools"],
    #                                     tp_lib_path=init["tp_lib_path"], output_dir=tmp_path, workers=2)
    #     out = capsys.readouterr().out
    #     captured_out_lines = out.split("\n")
    #     sys.stdout.write(out)
    #     output_dir = get_result_output_dir(captured_out_lines)
    #     assert (output_dir and output_dir.iterdir())
    #     logfile = get_logfile_path(captured_out_lines)
    #     assert logfile and logfile.is_file()
    #
    #
    # def test_sast_report_1(self, tmp_path, capsys, mocker):
    #     init = {}
    #     init_sastreport_test(init, mocker)
    #     # Test 1: it does not consider the following params
    #     # - export_file: Path = None,
    #     # - output_dir: Path = Path(config.RESULT_DIR).resolve(),
    #     # - only_last_measurement: bool = True):
    #     interface.report_sast_measurement_for_pattern_list(
    #         init["tools"], init["language"], init["patterns"], init["tp_lib_path"]
    #     )
    #     out = capsys.readouterr().out
    #     captured_out_lines = out.split("\n")
    #     sys.stdout.write(out)
    #     output_dir = get_result_output_dir(captured_out_lines)
    #     assert (output_dir and output_dir.iterdir())
    #     logfile = get_logfile_path(captured_out_lines)
    #     assert logfile and logfile.is_file()
    #
    #
    # def test_sast_report_2(self, tmp_path, capsys, mocker):
    #     init = {}
    #     init_sastreport_test(init, mocker)
    #     export_file = "test_export.csv"
    #     # Test 2: it does not consider the following params
    #     # - only_last_measurement: bool = True):
    #     interface.report_sast_measurement_for_pattern_list(
    #         init["tools"], init["language"], init["patterns"], init["tp_lib_path"],
    #         export_file=export_file, output_dir=tmp_path
    #     )
    #     out = capsys.readouterr().out
    #     captured_out_lines = out.split("\n")
    #     sys.stdout.write(out)
    #     output_dir = get_result_output_dir(captured_out_lines)
    #     assert (output_dir and output_dir.iterdir())
    #     logfile = get_logfile_path(captured_out_lines)
    #     assert logfile and logfile.is_file()
    #     assert (output_dir / export_file).is_file()
    #
    #
    # def test_check_discovery_rules_1(self, tmp_path, capsys, mocker):
    #     init = {}
    #     self._init_discovery_test(tmp_path, mocker)
    #     init_test(init)
    #     export_file = "test_export.csv"
    #     interface.check_discovery_rules(
    #         init["language"], init["patterns"], 0,
    #         tp_lib_path=init["tp_lib_path"], export_file=export_file
    #     )
    #     out = capsys.readouterr().out
    #     captured_out_lines = out.split("\n")
    #     sys.stdout.write(out)
    #     output_dir = get_result_output_dir(captured_out_lines)
    #     assert (output_dir and output_dir.iterdir())
    #     logfile = get_logfile_path(captured_out_lines)
    #     assert logfile and logfile.is_file()
    #
    #
    # def test_check_discovery_rules_2(self, tmp_path, capsys, mocker):
    #     init = {}
    #     self._init_discovery_test(tmp_path, mocker)
    #     init_test(init)
    #     export_file = "test_export.csv"
    #     interface.check_discovery_rules(
    #         init["language"], init["patterns"], 0,
    #         tp_lib_path=init["tp_lib_path"], export_file=export_file, output_dir=tmp_path
    #     )
    #     out = capsys.readouterr().out
    #     captured_out_lines = out.split("\n")
    #     sys.stdout.write(out)
    #     output_dir = get_result_output_dir(captured_out_lines)
    #     assert (output_dir and output_dir.iterdir())
    #     logfile = get_logfile_path(captured_out_lines)
    #     assert logfile and logfile.is_file()
    #
    #
    # def init_check_discovery_rules_3(self, init, tmp_path, mocker):
    #     init["language"] = "PHP"
    #     init["patterns"] = [32, 37]
    #     init["tp_lib_path"] = join_resources_path("sample_patlib_issue9")
    #     mocker.patch("core.discovery.run_generate_cpg_cmd",
    #                  return_value="Done",
    #                  side_effect=create_mock_cpg(tmp_path / "cpg_binary.bin"))
    #     mocker.patch("core.discovery.run_joern_scala_query_for_test",
    #                  return_value="Done")
    #     exp_discovery_rule_results = (
    #         str(join_resources_path("sample_joern") / "binary.bin"),
    #         "1_static_variables_iall",
    #         1
    #     )
    #     mocker.patch("core.discovery.run_and_process_discovery_rule",
    #                  return_value=bytes(str(exp_discovery_rule_results), 'utf-8'))
    #
    #
    # def test_check_discovery_rules_3(self, tmp_path, capsys, mocker):
    #     init = {}
    #     self.init_check_discovery_rules_3(init, tmp_path, mocker)
    #     export_file = "test_export.csv"
    #     interface.check_discovery_rules(
    #         init["language"], init["patterns"], 0,
    #         tp_lib_path=init["tp_lib_path"], export_file=export_file, output_dir=tmp_path
    #     )
    #     out = capsys.readouterr().out
    #     captured_out_lines = out.split("\n")
    #     sys.stdout.write(out)
    #     output_dir = get_result_output_dir(captured_out_lines)
    #     assert (output_dir and output_dir.iterdir())
    #     logfile = get_logfile_path(captured_out_lines)
    #     assert logfile and logfile.is_file()
    #
    #
    # def test_repair_patterns_not_including_readme(self):
    #     sample_tp_lib = join_resources_path("sample_patlib")
    #     test_pattern = create_pattern()
    #     with patch("core.pattern.Pattern.init_from_id_and_language") as init_pattern_mock, \
    #         patch("core.pattern.Pattern.repair") as patternrepair_mock, \
    #         patch("core.utils.check_file_exist") as check_file_exists_mock, \
    #         patch("core.utils.check_measurement_results_exist") as measurement_result_exist_mock, \
    #         patch("pathlib.Path.mkdir") as mkdir_mock:
    #         init_pattern_mock.return_value = test_pattern
    #         interface.repair_patterns("JS", [1,2,3], None, True, Path("measurements"), Path("dr_results.csv"), Path("out"), sample_tp_lib)
    #
    #     patternrepair_mock.assert_called_with(False,
    #                                           discovery_rule_results=Path("dr_results.csv"),
    #                                           measurement_results=Path("measurements"),
    #                                           masking_file=None)
    #     expected_calls = [call(1, "JS", sample_tp_lib), call(2, "JS", sample_tp_lib), call(3, "JS", sample_tp_lib)]
    #     init_pattern_mock.assert_has_calls(expected_calls)
    #     check_file_exists_mock.assert_not_called()
    #     measurement_result_exist_mock.assert_not_called()
    #     mkdir_mock.assert_called()
    #
    # def test_repair_patterns_not_including_readme(self):
    #     sample_tp_lib = join_resources_path("sample_patlib")
    #     test_pattern = create_pattern()
    #     with patch("core.pattern.Pattern.init_from_id_and_language") as init_pattern_mock, \
    #         patch("core.pattern.Pattern.repair") as patternrepair_mock, \
    #         patch("core.utils.check_file_exist") as check_file_exists_mock, \
    #         patch("core.utils.check_measurement_results_exist") as measurement_result_exist_mock, \
    #         patch("pathlib.Path.mkdir") as mkdir_mock:
    #         init_pattern_mock.return_value = test_pattern
    #         interface.repair_patterns("JS", [1,2,3], None, False, Path("measurements"), Path("dr_results.csv"), Path("out"), sample_tp_lib)
    #
    #     patternrepair_mock.assert_called_with(True,
    #                                           discovery_rule_results=Path("dr_results.csv"),
    #                                           measurement_results=Path("measurements"),
    #                                           masking_file=None)
    #     expected_calls = [call(1, "JS", sample_tp_lib), call(2, "JS", sample_tp_lib), call(3, "JS", sample_tp_lib)]
    #     init_pattern_mock.assert_has_calls(expected_calls)
    #     check_file_exists_mock.assert_called()
    #     measurement_result_exist_mock.assert_called_once()
    #     mkdir_mock.assert_called()
