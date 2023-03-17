from pathlib import Path
from typing import Dict
import shutil
import sys
import json

import pytest
from pytest_mock import MockerFixture

import config
from core import utils
from core import discovery, instance
from core.exceptions import MeasurementNotFound, CPGGenerationError
from qualitytests_utils import join_resources_path, get_result_output_dir


class TestDiscovery:
    testdir = Path(__file__).parent.parent.resolve()

    def test_discovery_1(self, mocker: MockerFixture, capsys, tmp_path):
        samples_src_dir: Path = join_resources_path("sample_tarpit")
        sample_tp_lib: Path = join_resources_path("sample_patlib")
        output_dir = join_resources_path("../temp").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        tools: list[Dict] = [{
            "name": "dummyTool",
            "version": "1"
        }]
        language = "PHP"
        mocked_tool_interface: Dict = {
            "supported_languages": ["PHP"],
            "tool_interface": "qualitytests.core.sast_test.SastTest"
        }
        mocker.patch("core.utils.load_sast_specific_config", return_value=mocked_tool_interface)
        mocker.patch("core.discovery.generate_cpg", return_value=None)
        mocker.patch("core.discovery.discovery_for_tool", return_value=[])
        mocker.patch.object(config, "RESULT_DIR", tmp_path)
        build_name, disc_output_dir = utils.get_operation_build_name_and_dir("discovery", samples_src_dir, language, output_dir)
        d_res = discovery.discovery(samples_src_dir, [1, 2], sample_tp_lib, tools, language, build_name, disc_output_dir)
        assert d_res["used_measured_patterns_ids"] == [1,2]
        assert d_res["ignored_not_measured_patterns_ids"] == []
        assert any(Path(d_res["discovery_result_file"]).name == e.name for e in disc_output_dir.iterdir())


    def test_discovery_2(self, mocker: MockerFixture, capsys, tmp_path, caplog):
        # Test JS patterns for which some has no discovery method specified
        samples_src_dir: Path = join_resources_path("sample_tarpit")
        sample_tp_lib: Path = join_resources_path("sample_patlib")
        output_dir = join_resources_path("../temp").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        tools: list[Dict] = [{
            "name": "dummyTool",
            "version": "1"
        }]
        language = "JS"
        mocked_tool_interface: Dict = {
            "supported_languages": ["JS"],
            "tool_interface": "qualitytests.core.sast_test.SastTest"
        }
        mocker.patch("core.utils.load_sast_specific_config", return_value=mocked_tool_interface)
        mocker.patch("core.discovery.generate_cpg",
                     return_value=tmp_path / "cpg_binary.bin",
                     side_effect=self._create_mock_cpg(tmp_path / "cpg_binary.bin"))

        # with open(join_resources_path("sample_joern") / "joern_discovery_query_res.json", "r") as data_file:
        #     joern_res = json.load(data_file)

        with open(join_resources_path("sample_joern") / "joern_discovery_scala_rule_res.txt", "r") as data_file:
            exp_joern_res = bytes(data_file.read(), 'utf-8-sig')
        # mocker.patch("core.discovery.subprocess.check_output",
        #              return_value=exp_joern_res)
        mocker.patch("core.discovery.run_discovery_rule_cmd",
                     return_value=exp_joern_res)
        mocker.patch.object(config, "RESULT_DIR", tmp_path)
        build_name, disc_output_dir = utils.get_operation_build_name_and_dir("discovery", samples_src_dir, language, output_dir)
        d_res = discovery.discovery(samples_src_dir, [1, 2], sample_tp_lib, tools, language, build_name, disc_output_dir)
        assert d_res["used_measured_patterns_ids"] == [2]
        assert d_res["ignored_not_measured_patterns_ids"] == [1]
        assert any(Path(d_res["discovery_result_file"]).name == e.name for e in disc_output_dir.iterdir())
        assert any(f"No discovery method has been specified. Likely you need to modify the discovery->method property" in record.message for record in caplog.records)


    # TODO
    @pytest.mark.skip()
    def test_manualdiscovery(self):
        pass

    def test_run_discovery_rule(self, mocker):
        discovery_rule: Path = join_resources_path("sample_patlib/PHP/1_static_variables/1_instance_1_static_variables/1_instance_1_static_variables.sc")
        with open(join_resources_path("sample_joern") / "joern_discovery_scala_rule_res.txt", "r") as data_file:
            exp_joern_res = bytes(data_file.read(), 'utf-8-sig')
        cpg: Path = join_resources_path("sample_joern/cpg_binary.bin")
        mocker.patch("core.discovery.subprocess.check_output",
                     return_value=exp_joern_res)
        _cpg, query, findings = discovery.run_discovery_rule(cpg, discovery_rule, "joern")
        assert findings[0]["lineNumber"] == 4


    # TODO: we will refactor that code anyhow
    @pytest.mark.skip()
    def test_discovery_for_tool(self):
        samples_dir: Path = Path(__file__).resolve().parent / "testing_samples"
        instance.load_instance_from_metadata()
        assert 0

    def _create_mock_cpg(self, dst_file):
        sample_cpg_binary: Path = join_resources_path("sample_joern/cpg_binary.bin")
        shutil.copy(sample_cpg_binary, dst_file )

    def test_generate_cpg_1(self, tmp_path, capsys, mocker):
        mocker.patch("core.discovery.run_generate_cpg_cmd",
                     return_value="Done",
                     side_effect=self._create_mock_cpg(tmp_path / "cpg_binary.bin"))
        mocker.patch("core.discovery.run_joern_scala_query_for_test",
                     return_value="Done")
        discovery.generate_cpg("whatever", "PHP", "test", tmp_path)
        assert Path.is_file(tmp_path / "cpg_binary.bin")


    def test_generate_cpg_2(self, tmp_path, capsys, mocker):
        mocker.patch("core.discovery.run_generate_cpg_cmd",
                     return_value="Done",
                     side_effect=Exception())
        mocker.patch("core.discovery.run_joern_scala_query_for_test",
                     return_value="Done")
        with pytest.raises(CPGGenerationError):
            discovery.generate_cpg("whatever", "PHP", "test", tmp_path)


    def test_generate_cpg_3(self, tmp_path, capsys, mocker):
        mocker.patch("core.discovery.run_generate_cpg_cmd",
                     return_value="Done",
                     side_effect=self._create_mock_cpg(tmp_path / "cpg_binary.bin"))
        mocker.patch("core.discovery.run_joern_scala_query_for_test",
                     return_value="Done, but Error in CPG generation...")
        with pytest.raises(CPGGenerationError):
            discovery.generate_cpg("whatever", "PHP", "test", tmp_path)


    def test_generate_cpg_4(self, tmp_path, capsys, mocker):
        mocker.patch("core.discovery.run_generate_cpg_cmd",
                     return_value="Done",
                     side_effect=self._create_mock_cpg(tmp_path / "cpg_binary.bin"))
        mocker.patch("core.discovery.run_joern_scala_query_for_test",
                     return_value="Done, but Error in CPG generation...",
                     side_effect=Exception())
        with pytest.raises(CPGGenerationError):
            discovery.generate_cpg("whatever", "PHP", "test", tmp_path)


    def test_patch_PHP_discovery_rule_1(self, tmp_path):
        language = "PHP"
        dr: Path = join_resources_path("sample_patlib/PHP/3_global_array/1_instance_3_global_array/1_instance_3_global_array.sc")
        pdr = discovery.patch_PHP_discovery_rule(dr, language)
        assert Path.is_file(pdr)
        assert str(dr.parent) in str(pdr)


    def test_patch_PHP_discovery_rule_2(self, tmp_path):
        language = "PHP"
        dr: Path = join_resources_path(
            "sample_patlib/PHP/3_global_array/1_instance_3_global_array/1_instance_3_global_array.sc")
        pdr = discovery.patch_PHP_discovery_rule(dr, language, output_dir=tmp_path)
        assert Path.is_file(pdr)
        assert str(tmp_path) in str(pdr)
