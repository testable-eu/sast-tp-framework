from pathlib import Path
from typing import Dict
import json
import sys

import pytest

pytest_plugins = ('pytest_asyncio',)

from cli import interface
from core.errors import measurementNotFound

from qualitytests_utils import join_resources_path, create_mock_cpg, \
    get_result_output_dir, get_logfile_path, in_logfile, init_measure_test


@pytest.mark.asyncio
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
        mocker.patch("core.utils.load_sast_specific_config", return_value=mocked_tool_interface)
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
        mocker.patch("core.discovery.run_discovery_rule", return_value=exp_discovery_rule_results)
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




    # @pytest.fixture
    # def event_loop(self):
    #     loop = asyncio.get_event_loop()
    #     yield loop
    #     loop.close()

    @pytest.mark.asyncio
    async def test_sast_measurement(self, tmp_path, capsys, mocker):
        init = {}
        init_measure_test(init, mocker)
        await interface.measure_list_patterns(init["patterns"], init["language"], tools=init["tools"],
                                        tp_lib_path=init["tp_lib_path"])
        out = capsys.readouterr().out
        captured_out_lines = out.split("\n")
        sys.stdout.write(out)
        output_dir = get_result_output_dir(captured_out_lines)
        assert (output_dir and output_dir.iterdir())
        logfile = get_logfile_path(captured_out_lines)
        assert logfile and logfile.is_file()

