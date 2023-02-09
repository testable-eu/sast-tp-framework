import uuid

import pytest
import asyncio
from pytest_mock import MockerFixture
pytest_plugins = ('pytest_asyncio',)

import qualitytests_utils

from core import measure
from core.exceptions import PatternDoesNotExists

@pytest.mark.asyncio
class TestMeasure:


    async def test_raise_pattern_not_found_measure_pattern_by_pattern_id(self, tmp_path, capsys, caplog, mocker):
        init = {}
        qualitytests_utils.init_measure_test(init, mocker)
        assert init["patterns"] == [1,2,3]
        pattern_id: int = 2
        mocker.patch("core.pattern_operations.start_add_measurement_for_pattern",
                     side_effect=PatternDoesNotExists(pattern_id))
        d_res = await measure.measure_list_patterns([pattern_id], init["language"], init["tools"], init["tp_lib_path"], tmp_path, 3)
        assert any(f"pattern {pattern_id} not found" in record.message for record in caplog.records)
        assert len(d_res['sast_job_collection_error']) == 1


    async def test_measure_list_patterns(self, tmp_path, mocker: MockerFixture):
        init = {}
        qualitytests_utils.init_measure_test(init, mocker, exception=False)
        assert init["patterns"] == [1, 2, 3]
        d_res = await measure.measure_list_patterns([1, 2],
                                                    init["language"],
                                                    init["tools"],
                                                    init["tp_lib_path"],
                                                    tmp_path, 1)
        assert len(d_res['sast_job_execution_error']) == 0
        assert len(d_res['sast_job_collection_error']) == 0


    # TODO: the test works fine when it is run on its own,
    #       but it does not terminate when run in a test batch.
    #       To be investigated...

    async def test_measure_list_patterns_with_sastmockexception(self, tmp_path, caplog, mocker: MockerFixture):
        init = {}
        qualitytests_utils.init_measure_test(init, mocker, exception=True)
        assert init["patterns"] == [1, 2, 3]
        d_res = await measure.measure_list_patterns(init["patterns"], init["language"],
                                                    init["tools"],
                                                    init["tp_lib_path"],
                                                    tmp_path, 3)
        assert len(d_res['sast_job_execution_error']) == 4
        assert len(d_res['sast_job_collection_error']) == 0
        assert len(d_res['sast_job_execution_valid']) == 8
        for record in caplog.records:
            print(record.message)