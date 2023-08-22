from datetime import datetime
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest
from core import pattern_operations
from core.measurement import Measurement

from qualitytests.qualitytests_utils import create_pattern, join_resources_path


class TestPatternOperations:
    def test_add_testability_pattern_to_lib(self):
        test_pattern = create_pattern()
        json_path = test_pattern.json_path
        pattern_dir = test_pattern.path
        tp_lib_dest = Path("/tp_framework/tp_lib")
        with patch("core.pattern.Pattern.init_from_json_file_without_pattern_id") as init_pattern_mock, \
            patch("core.pattern.Pattern.copy_to_tplib") as copy_mock, \
            patch("core.pattern_operations.logger.info") as logger_info_mock:
            init_pattern_mock.return_value = test_pattern

            pattern_operations.add_testability_pattern_to_lib_from_json("js", json_path, pattern_dir, tp_lib_dest)
        
        init_pattern_mock.assert_called_once_with(json_path, "js", pattern_dir, tp_lib_dest)
        copy_mock.assert_called_once()
        logger_info_mock.assert_called_once_with(f"The pattern has been copied to {pattern_dir}, You might need to adjust relative path links.")

    @pytest.mark.asyncio
    async def test_add_measurement_for_pattern(self):
        sample_tp_lib: Path = join_resources_path("sample_patlib")
        test_pattern = create_pattern()
        now = datetime.now()
        with patch("core.pattern.Pattern.init_from_id_and_language") as pattern_init_mock, \
            patch("core.pattern_operations.logger.warning") as warn_logger_mock, \
            patch("core.analysis.analyze_pattern_instance") as analyze_mock:
            pattern_init_mock.return_value = test_pattern
            await pattern_operations.start_add_measurement_for_pattern("js", [{"dummyTool": "saas"}], 1, now, sample_tp_lib, Path("non_existing_dir"))
        
        pattern_init_mock.assert_called_once_with(1, "js", sample_tp_lib)
        warn_logger_mock.assert_not_called()
        analyze_mock.assert_awaited_once_with(test_pattern.instances[0], [{"dummyTool": "saas"}], "js", now, Path("non_existing_dir"))

    @pytest.mark.asyncio
    async def test_save_measurement_for_pattern(self):
        test_pattern = create_pattern()
        fake_measurement = Measurement(datetime.now(), False, True, "some_tool", "saas", test_pattern.instances[0])
        open_mock = mock_open()
        with patch("core.pattern_operations.job_list_to_dict") as job_list_to_dict_mock, \
            patch("core.analysis.inspect_analysis_results") as inspect_analysis_results_mock, \
            patch("core.pattern_operations.meas_list_to_tp_dict") as meas_list_to_tp_dict_mock, \
            patch("core.pattern.Pattern.init_from_id_and_language") as pattern_init_mock, \
            patch("core.utils.get_measurement_dir_for_language") as measurement_dir_for_lang_mock, \
            patch("pathlib.Path.mkdir") as mkdir_mock, \
            patch("builtins.open", open_mock, create=True), \
            patch("json.dump") as json_dump_mock:

            meas_list_to_tp_dict_mock.return_value = {1: {1: [fake_measurement]}}
            measurement_dir_for_lang_mock.return_value = Path("/")
            pattern_init_mock.return_value = test_pattern
            await pattern_operations.save_measurement_for_patterns("js", datetime.now(), ["list_of_sast_jobs"], Path("samplelib"))
        
        job_list_to_dict_mock.assert_called_once_with(["list_of_sast_jobs"])
        inspect_analysis_results_mock.assert_called_once_with(job_list_to_dict_mock.return_value, "js")
        meas_list_to_tp_dict_mock.assert_called_with(inspect_analysis_results_mock.return_value)
        pattern_init_mock.assert_called_once_with(1, "js", Path("samplelib"))
        measurement_dir_for_lang_mock.assert_called_once_with(Path("samplelib"), "js")
        mkdir_mock.assert_called_once()
        d_tpi_meas_expected = {
            "pattern_id": 1,
            "instance_id": 1,
            "language": "JS",
            "instance": "keks"
        }
        d_tpi_meas_expected.update(vars(fake_measurement))
        l_tpi_meas_expected = [d_tpi_meas_expected]
        json_dump_mock.assert_called_once_with(l_tpi_meas_expected, open_mock.return_value, indent=4)
