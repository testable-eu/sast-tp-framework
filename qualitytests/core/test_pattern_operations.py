import json
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path, WindowsPath
from typing import Dict

import pytest
from freezegun import freeze_time

from core import pattern_operations
from core.exceptions import PatternValueError
from core.instance import PatternCategory, FeatureVsInternalApi, Instance
from core.measurement import Measurement
from core.pattern import Pattern


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

    pattern1: Dict = {
        "name": "Pattern One",
        "description": "",
        "family": "None",
        "tags": [],
        "instances": [
            "./1_instance_1_pattern_one/1_instance_1_pattern_one.json",
            "./2_instance_1_pattern_one/2_instance_1_pattern_one.json"
        ]
    }
    with open(p1 / (p1.name + ".json"), "w") as pattern_json_file:
        json.dump(pattern1, pattern_json_file, indent=4)

    pattern2: Dict = {
        "name": "Pattern Two",
        "description": "",
        "family": "None",
        "tags": [],
        "instances": [
            "./1_instance_2_pattern_two/1_instance_2_pattern_two.json",
            "./2_instance_2_pattern_two/2_instance_2_pattern_two.json"
        ]
    }
    with open(p2 / (p2.name + ".json"), "w") as pattern_json_file:
        json.dump(pattern2, pattern_json_file, indent=4)

    pattern3: Dict = {
        "name": "Pattern Three",
        "description": "",
        "family": "None",
        "tags": [],
        "instances": [
            "./1_instance_3_pattern_three/1_instance_3_pattern_three.json",
            "./2_instance_3_pattern_three/2_instance_3_pattern_three.json"
        ]
    }
    with open(p3 / (p3.name + ".json"), "w") as pattern_json_file:
        json.dump(pattern3, pattern_json_file, indent=4)

    return language, tmp_tp_path, p1, p2, p3


def setup_two_instances(p_path: Path):
    pi1_path = p_path / ("1_instance_" + p_path.name)
    pi2_path = p_path / ("2_instance_" + p_path.name)
    pi1_path.mkdir()
    pi2_path.mkdir()

    instance_dict: Dict = {
        "code": "./instance_one.php",
        "discovery": {
            "rule": "./instance_one.sc",
            "method": None,
            "rule_accuracy": None
        },
        "transformation": "",
        "version": "1",
        "compile": {
            "binary": "./instance_one.bash",
            "instruction": None
        },
        "expectation": {
            "type": "xss",
            "sink_file": "./instance_one.php",
            "sink_line": 18,
            "source_file": "./instance_one.php",
            "source_line": 17,
            "expectation": True
        },
        "properties": {
            "category": "D2",
            "feature_vs_internal_api": "FEATURE",
            "input_sanitizer": False,
            "source_and_sink": False,
            "negative_test_case": False
        },
        "measurements": []
    }

    with open(pi1_path / (pi1_path.name + ".json"), "w") as instance_json_file:
        json.dump(instance_dict, instance_json_file, indent=4)

    with open(pi2_path / (pi2_path.name + ".json"), "w") as instance_json_file:
        json.dump(instance_dict, instance_json_file, indent=4)

    return pi1_path, pi2_path


class TestPatternOperations:

    # TODO: most of these tests need to be updated and do not work

    def test_add_testability_pattern_to_lib(self, tmp_path):
        language, tmp_tp_path, p1, p2, p3 = setup_three_pattern(tmp_path)
        pattern: Dict = {
            "name": "Try Catch Finally",
            "description": "",
            "family": "None",
            "tags": [],
            "instances": [
                "./1_instance_52_try_catch_finally/1_instance_52_try_catch_finally.json",
                "./2_instance_52_try_catch_finally/2_instance_52_try_catch_finally.json"
            ]
        }

        pattern_operations.add_testability_pattern_to_lib(language, pattern, None, tmp_path)

        expected_new_pattern_path: Path = tmp_tp_path / "4_try_catch_finally"
        expected_new_pattern_json_path: Path = expected_new_pattern_path / "4_try_catch_finally.json"
        with open(expected_new_pattern_json_path) as json_file:
            pattern_from_tp_lib = json.load(json_file)

        assert pattern["name"] == pattern_from_tp_lib["name"]
        assert pattern_from_tp_lib["instances"] == []

    def test_add_testability_pattern_to_lib_with_value_error(self, tmp_path):
        language, tmp_tp_path, p1, p2, p3 = setup_three_pattern(tmp_path)
        pattern: Dict = {
            "description": "",
            "family": "None",
            "tags": [],
            "instances": [
                "./1_instance_52_try_catch_finally/1_instance_52_try_catch_finally.json",
                "./2_instance_52_try_catch_finally/2_instance_52_try_catch_finally.json"
            ]
        }

        with pytest.raises(PatternValueError):
            pattern_operations.add_testability_pattern_to_lib(language, pattern, None, tmp_path)

    def test_add_testability_pattern_to_lib_from_json(self, tmp_path):
        language, tmp_tp_path, p1, p2, p3 = setup_three_pattern(tmp_path)
        json_path: Path = (
                Path(__file__).resolve().parent / "testing_samples" / "sample_pattern" / "try_catch_finally.json"
        )

        pattern_operations.add_testability_pattern_to_lib_from_json(language, json_path, json_path.parent, tmp_path)

        actual_pattern_path: Path = tmp_tp_path / "4_try_catch_finally"
        actual_pattern_json_path: Path = actual_pattern_path / "4_try_catch_finally.json"
        with open(actual_pattern_json_path) as json_file:
            actual_pattern = json.load(json_file)

        with open(json_path) as json_file:
            expected_pattern = json.load(json_file)

        assert expected_pattern["name"] == actual_pattern["name"]
        assert actual_pattern["instances"] == [
            './1_instance_4_try_catch_finally/1_instance_4_try_catch_finally.json',
            './2_instance_4_try_catch_finally/2_instance_4_try_catch_finally.json'
        ]

    def test_add_testability_pattern_to_lib_from_json_bad_encoding(self, tmp_path):
        language, tmp_tp_path, p1, p2, p3 = setup_three_pattern(tmp_path)
        json_path: Path = (
                Path(__file__).resolve().parent / "testing_samples" / "sample_broken_pattern" / "try_catch_finally_broken.json"
        )

        with pytest.raises(JSONDecodeError):
            pattern_operations.add_testability_pattern_to_lib_from_json(language, json_path, json_path.parent, tmp_path)

    def test_add_testability_pattern_to_lib_from_json_with_missing_field(self, tmp_path):
        language, tmp_tp_path, p1, p2, p3 = setup_three_pattern(tmp_path)
        json_path: Path = (
                Path(__file__).resolve().parent / "testing_samples" / "sample_broken_pattern" / "try_catch_finally.json"
        )

        with pytest.raises(PatternValueError):
            pattern_operations.add_testability_pattern_to_lib_from_json(language, json_path, json_path.parent, tmp_path)

    def test_add_tp_instance_to_lib(self, tmp_path):
        language, tmp_tp_path, p1, p2, p3 = setup_three_pattern(tmp_path)
        pi1 = p2 / ("1_instance" + p2.name)
        pi2 = p2 / ("2_instance" + p2.name)
        pi1.mkdir()
        pi2.mkdir()

        pattern = Pattern("Try Catch Finally", language, [], "FAMILY", "TestDesc", [], pattern_id=4)

        source_path: Path = Path(__file__).resolve().parent / "testing_samples" / "sample_pattern"

        exp_instance: Dict = {
            "code": "./instance_one.php",
            "discovery": {
                "rule": "./instance_one.sc",
                "method": None,
                "rule_accuracy": None
            },
            "transformation": "",
            "version": "1",
            "compile": {
                "binary": "./instance_one.bash",
                "instruction": None
            },
            "expectation": {
                "type": "xss",
                "sink_file": "./instance_one.php",
                "sink_line": 18,
                "source_file": "./instance_one.php",
                "source_line": 17,
                "expectation": True
            },
            "properties": {
                "category": "D2",
                "feature_vs_internal_api": "FEATURE",
                "input_sanitizer": False,
                "source_and_sink": False,
                "negative_test_case": False
            },
            "measurements": []
        }

        pattern_operations.add_tp_instance_to_lib(language, pattern, exp_instance, "instance_one", source_path,
                                                  tmp_path)

        actual_instance_path: Path = tmp_tp_path / "4_try_catch_finally" / "1_instance_4_try_catch_finally"
        actual_pattern_json_path: Path = actual_instance_path / "1_instance_4_try_catch_finally.json"
        with open(actual_pattern_json_path) as act_json_file:
            actual_instance = json.load(act_json_file)

        assert exp_instance["expectation"]["type"] == actual_instance["expectation"]["type"]
        assert actual_instance["code"] == "./instance_one.php"
        assert actual_instance["compile"]["binary"] == "./instance_one.bash"
        assert actual_instance["expectation"]["sink_file"] == "./instance_one.php"
        assert actual_instance["expectation"]["source_file"] == "./instance_one.php"
        assert actual_instance["discovery"]["rule"] == "./instance_one.sc"

    @freeze_time(datetime.now())
    async def test_add_measurement_for_pattern(self, tmp_path, mocker):
        language, tmp_tp_path, p1, p2, p3 = setup_three_pattern(tmp_path)
        pi1 = p2 / ("1_instance_" + p2.name)
        pi1.mkdir()
        instance_dict: Dict = {
            "code": "./instance_one.php",
            "discovery": {
                "rule": "./instance_one.sc",
                "method": None,
                "rule_accuracy": None
            },
            "transformation": "",
            "version": "1",
            "compile": {
                "binary": "./instance_one.bash",
                "instruction": None
            },
            "expectation": {
                "type": "xss",
                "sink_file": "./instance_one.php",
                "sink_line": 18,
                "source_file": "./instance_one.php",
                "source_line": 17,
                "expectation": True
            },
            "properties": {
                "category": "D2",
                "feature_vs_internal_api": "FEATURE",
                "input_sanitizer": False,
                "source_and_sink": False,
                "negative_test_case": False
            },
            "measurements": []
        }

        with open(pi1 / (pi1.name + ".json"), "w") as instance_json_file:
            json.dump(instance_dict, instance_json_file, indent=4)

        pi1_meas: Path = tmp_path / "measurements" / language / "2_pattern_two/1_instance_2_pattern_two"

        current_time: datetime = datetime.now()
        date_time_str_file = current_time.strftime("%Y-%m-%d_%H-%M-%S")
        date_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        exp_instance1: Instance = Instance(
            name='Pattern Two',
            definition='What happens for the variables inside the function when the function finish simply they die! and if we run the function again, we will have new variables. But if we want to keep the variable life, we have to use static. At the same time, static variables are challenges for the scanners, because the scanner has to record the last value for the variable with the last call for the function.',
            family="",
            tags=[],
            instances=[Path('./1_instance_2_pattern_two/1_instance_2_pattern_two.json')],
            language='PHP',
            pattern_id=2,
            code=Path('1_instance_2_pattern_two.php'),
            compile_binary=Path('1_instance_2_pattern_two.bash'),
            version='1',
            properties_category=PatternCategory.S0,
            properties_negative_test_case=False,
            properties_source_and_sink=False,
            properties_input_sanitizer=False,
            properties_feature_vs_internal_api=FeatureVsInternalApi.FEATURE,
            expectation=True,
            discovery_rule=Path('1_instance_2_pattern_two.sc'),
            discovery_method="",
            discovery_rule_accuracy="",
            expectation_type='xss',
            expectation_sink_file=Path('1_instance_2_pattern_two.php'),
            expectation_sink_line=5,
            expectation_source_file=Path('1_instance_2_pattern_two.php'),
            expectation_source_line=9,
            instance_id=1,
        )

        exp_measurements: list[Measurement] = [
            Measurement(
                date=date_time_str,
                result=True,
                expected_result=True,
                tool="dummyTool",
                version="1",
                instance=exp_instance1,

            )
        ]

        mocker.patch("core.pattern_operations.analysis.analyze_pattern_instance", return_value=exp_measurements)
        sast_tools: Dict = {
            "name": "dummyTool",
            "version": "1"
        }

        await pattern_operations.start_add_measurement_for_pattern(language, [sast_tools], 2, tmp_path, tmp_path)
        assert list(pi1_meas.iterdir())[0].name == "measurement-{}.json".format(date_time_str_file)

        with open(list(pi1_meas.iterdir())[0]) as meas_json:
            assert len(json.load(meas_json)) == 1
