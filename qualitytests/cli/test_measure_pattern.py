import uuid
from pathlib import Path
from typing import Dict
from unittest.mock import Mock

import pytest
import asyncio
from pytest_mock import MockerFixture
pytest_plugins = ('pytest_asyncio',)

import qualitytests_utils

from cli import measure_pattern
from core.exceptions import PatternDoesNotExists

#TODO: to be adjusted!

@pytest.mark.asyncio
class TestMeasurePattern:

    #@pytest.mark.skip()s
    async def test_raise_pattern_not_found_measure_pattern_by_pattern_id(self, tmp_path, capsys, mocker):
        test_lib: Path = tmp_path / "test_lib"
        language: str = "JS"
        pattern_id: int = 2
        test_lib.mkdir()
        (test_lib / language).mkdir()
        tools: list[Dict] = [{
            "name": "codeql",
            "version": "2.9.2"
        }]
        sample_tp_lib: Path = qualitytests_utils.join_resources_path("sample_patlib")
        # mytest = "DEBUG 123456"
        # print(mytest)
        # captured = capsys.readouterr()
        # assert mytest not in captured.out
        await measure_pattern.measure_list_patterns([pattern_id], language, tools, str(sample_tp_lib), 3)
        #measure_pattern.measure_pattern_by_pattern_id(pattern_id, language, tools, str(test_lib))
        mocker.patch("cli.measure_pattern.pattern_operations.add_measurement_for_pattern",
                     side_effect=PatternDoesNotExists(pattern_id))
        captured = capsys.readouterr()
        assert captured.out == f"Specified Pattern `{pattern_id}` does not exists\n"

    async def test_measure_list_patterns(self, mocker: MockerFixture):
        tools: list[Dict] = [
            {
                "name": "fortify",
                "version": "20.2.4"
            }
        ]
        sample_tp_lib: Path = Path(__file__).resolve().parent.parent / "core/testing_samples" / "sample_patlib"
        task_mock = mocker.patch("cli.measure_pattern.pattern_operations.start_add_measurement_for_pattern",
                                 return_value=[uuid.uuid4() for _ in range(10)])
        mocker.patch("cli.measure_pattern.pattern_operations.save_measurement_for_pattern")
        await measure_pattern.measure_list_patterns([1, 2], "PHP", tools, str(sample_tp_lib), 3)

        assert task_mock.call_count == 2

    async def test_measure_list_patterns_non_existing_pattern(self, capsys, mocker):
        tools: list[Dict] = [
            {
                "name": "fortify",
                "version": "20.2.4"
            }
        ]
        sample_tp_lib: Path = Path(__file__).resolve().parent.parent / "core/testing_samples" / "sample_patlib"
        task_mock = mocker.patch("cli.measure_pattern.pattern_operations.start_add_measurement_for_pattern",
                                 side_effect=PatternDoesNotExists(10))
        await measure_pattern.measure_list_patterns([10], "PHP", tools, str(sample_tp_lib), 3)

        assert task_mock.call_count == 1
        captured = capsys.readouterr()
        assert captured.err == f"Specified Pattern `{10}` does not exists\n"

    async def test_measure_list_patterns_non_existing_tp_lib(self, capsys):
        tools: list[Dict] = [
            {
                "name": "fortify",
                "version": "20.2.4"
            }
        ]
        sample_tp_lib: Path = Path(__file__).resolve().parent.parent / "core/testing_samples" / "non_sample_patlib"
        await measure_pattern.measure_list_patterns([10], "PHP", tools, str(sample_tp_lib), 3)
        captured = capsys.readouterr()
        assert captured.err == f"Specified `{sample_tp_lib}` is not a folder or does not exists\n"

    async def test_measure_all_pattern(self, mocker: MockerFixture):
        tools: list[Dict] = [
            {
                "name": "fortify",
                "version": "20.2.4"
            }
        ]
        sample_tp_lib: Path = Path(__file__).resolve().parent.parent / "core/testing_samples" / "sample_patlib"
        measure_patch: Mock = mocker.patch("cli.measure_pattern.measure_list_patterns")
        await measure_pattern.measure_all_pattern("PHP", tools, str(sample_tp_lib))
        measure_patch.assert_called_once()
        measure_list_call_args = measure_patch.call_args_list
        exp_pattern_list = measure_list_call_args[0][0][0]
        assert sorted(exp_pattern_list) == [1, 2]


@pytest.mark.asyncio
async def test_integration_measurement(mocker):
    tools: list[Dict] = [
        {
            "name": "sast_test",
            "version": "1"
        }
    ]
    pattern_id_list: list[int] = list(range(1, 20))
    lang: str = "PHP"

    mocked_tool_interface: Dict = {
        "supported_languages": ["PHP"],
        "tool_interface": "tests.core.sast_test.SastTest"
    }

    mocker.patch("cli.measure_pattern.config.load_sast_specific_config", return_value=mocked_tool_interface)
    mocker.patch("core.analysis.config.load_sast_specific_config", return_value=mocked_tool_interface)
    await measure_pattern.measure_list_patterns(pattern_id_list, lang, tools, workers=5)
