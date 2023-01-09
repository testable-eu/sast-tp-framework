from typing import Dict

import pytest
import json
from pathlib import Path

from core.exceptions import PatternDoesNotExists, PatternValueError
from core.pattern import Pattern, pattern_from_dict, get_pattern_path_by_pattern_id


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

    return language, tmp_tp_path, p1, p2, p3


class TestPattern:

    def test_pattern_init_with_id(self):
        pattern = Pattern("TestName", "TestDesc", "FAMILY", [], [], "PHP", 1)
        assert pattern.pattern_id == 1
        assert pattern.name == "TestName"
        assert pattern.description == "TestDesc"
        assert pattern.family == "FAMILY"
        assert len(pattern.tags) == 0
        assert len(pattern.instances) == 0

    def test_pattern_init_without_id(self, tmp_path):
        language, tmp_tp_path, p1, p2, p3 = setup_three_pattern(tmp_path)
        pattern = Pattern("TestName", "TestDesc", "FAMILY", [], [], language, pattern_dir=tmp_path)
        assert pattern.pattern_id == 4
        assert pattern.name == "TestName"
        assert pattern.description == "TestDesc"
        assert pattern.family == "FAMILY"
        assert len(pattern.tags) == 0
        assert len(pattern.instances) == 0

    def test_pattern_init_without_id_and_empty_tp_library(self, tmp_path):
        language: str = "PHP"
        tmp_tp_path: Path = tmp_path / language
        tmp_tp_path.mkdir()
        pattern = Pattern("TestName", "TestDesc", "FAMILY", [], [], language, pattern_dir=tmp_path)
        assert pattern.pattern_id == 1
        assert pattern.name == "TestName"
        assert pattern.description == "TestDesc"
        assert pattern.family == "FAMILY"
        assert len(pattern.tags) == 0
        assert len(pattern.instances) == 0

    def test_pattern_non_existing_language(self, tmp_path):
        pattern: Pattern = Pattern("TestName", "TestDesc", "FAMILY", [], [], "JS", pattern_dir=tmp_path)
        assert pattern.pattern_id == 1

    def test_get_pattern_path_by_pattern_id(self, tmp_path):
        language, tmp_tp_path, p1, p2, p3 = setup_three_pattern(tmp_path)
        assert p3 == get_pattern_path_by_pattern_id(language, 3, tmp_path)

    def test_get_pattern_path_by_pattern_id_non_exist(self, tmp_path):
        language, tmp_tp_path, p1, p2, p3 = setup_three_pattern(tmp_path)
        with pytest.raises(PatternDoesNotExists):
            get_pattern_path_by_pattern_id(language, 5, tmp_path)

    # TODO: to be fixed
    @pytest.mark.skip()
    def test_add_pattern_to_tp_library(self, tmp_path):
        language: str = "PHP"
        tmp_tp_path: Path = tmp_path / language
        tmp_tp_path.mkdir()
        p1 = tmp_tp_path / "1_pattern_one"
        p1.mkdir()

        pattern: Pattern = Pattern("Pattern Two", "TestDesc", "FAMILY", [], [], language, pattern_dir=tmp_path)
        pattern.add_pattern_to_tp_library(language, tmp_path, tmp_path)

        expected_new_pattern_path: Path = tmp_tp_path / "2_pattern_two"
        expected_new_pattern_json_path: Path = expected_new_pattern_path / "2_pattern_two.json"
        with open(expected_new_pattern_json_path) as json_file:
            pattern_from_tp_lib = json.load(json_file)

        assert pattern.name == pattern_from_tp_lib["name"]
        assert pattern.description == pattern_from_tp_lib["definition"]
        assert len(pattern.instances) == len(pattern_from_tp_lib["instances"])

    # TODO: to be fixed
    @pytest.mark.skip()
    def test_add_pattern_to_tp_library_new_language(self, tmp_path):
        language: str = "JS"
        tmp_tp_path: Path = tmp_path / language

        pattern: Pattern = Pattern("Pattern One JS", "TestDesc", "FAMILY", [], [], language, pattern_dir=tmp_path)
        pattern.add_pattern_to_tp_library(language, tmp_path)

        expected_new_pattern_path: Path = tmp_tp_path / "1_pattern_one_js"
        expected_new_pattern_json_path: Path = expected_new_pattern_path / "1_pattern_one_js.json"
        with open(expected_new_pattern_json_path) as json_file:
            pattern_from_tp_lib = json.load(json_file)

        assert pattern.name == pattern_from_tp_lib["name"]
        assert pattern.description == pattern_from_tp_lib["definition"]
        assert len(pattern.instances) == len(pattern_from_tp_lib["instances"])

    # TODO: to be fixed
    @pytest.mark.skip()
    def test_add_new_instance_reference(self, tmp_path):
        language: str = "JS"
        tmp_tp_path: Path = tmp_path / language

        pattern: Pattern = Pattern("Pattern One JS", "TestDesc", "FAMILY", [], [], language, pattern_dir=tmp_path)
        pattern.add_pattern_to_tp_library(language, tmp_path)

        pattern.add_new_instance_reference(language, tmp_path, "./new_instance_test")

        expected_new_pattern_path: Path = tmp_tp_path / "1_pattern_one_js"
        expected_new_pattern_json_path: Path = expected_new_pattern_path / "1_pattern_one_js.json"
        with open(expected_new_pattern_json_path) as json_file:
            pattern_from_tp_lib = json.load(json_file)

        assert ["./new_instance_test"] == pattern_from_tp_lib["instances"]


    def test_pattern_from_dict(self):
        pattern_dict: Dict = {
            "name": "Try Catch Finally",
            "description": "",
            "family": "None",
            "tags": [],
            "instances": [
                "./1_instance_52_try_catch_finally/1_instance_52_try_catch_finally.json",
                "./2_instance_52_try_catch_finally/2_instance_52_try_catch_finally.json"
            ]
        }
        pattern = pattern_from_dict(pattern_dict, "PHP", 1)
        assert pattern.name == pattern_dict["name"]
        assert pattern.pattern_id == 1
        assert pattern.language == "PHP"
        assert pattern.instances == pattern_dict["instances"]


    def test_pattern_from_dict_missing_field(self):
        pattern_dict: Dict = {
            "name": "Try Catch Finally",
            "description": "",
            "tags": [],
            "instances": [
                "./1_instance_52_try_catch_finally/1_instance_52_try_catch_finally.json",
                "./2_instance_52_try_catch_finally/2_instance_52_try_catch_finally.json"
            ]
        }
        with pytest.raises(PatternValueError):
            pattern_from_dict(pattern_dict, "PHP", 1)
