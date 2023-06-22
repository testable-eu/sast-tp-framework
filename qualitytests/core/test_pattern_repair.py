import pytest
from pathlib import Path
from unittest.mock import patch

from core.pattern import Pattern
from core.pattern_repair import PatternRepair
from qualitytests.qualitytests_utils import join_resources_path


class MockedPattern:
    def __init__(self) -> None:
        self.tp_lib_path: Path = join_resources_path("sample_patlib")


class TestPatternRepair:
    mocked_pattern = MockedPattern()

    def test_repair_pattern_json(self):
        with patch("pathlib.Path.is_file") as is_file_mock_init:
            is_file_mock_init.return_value = True
            pattern_repair = PatternRepair(TestPatternRepair.mocked_pattern)
        
        is_file_mock_init.assert_called_once()

        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.utils.get_pattern_json") as get_pattern_json_mock, \
            patch("shutil.copy") as copy_mock:
            is_file_mock.return_value = False
            get_pattern_json_mock.return_value = None

            pattern_repair.repair_pattern_json()
        
        is_file_mock.assert_called_once()
        get_pattern_json_mock.assert_called_once()
        copy_mock.assert_called_once()

        