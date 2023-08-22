import pytest
from pathlib import Path
from unittest.mock import patch

from core.pattern import Pattern
from core.repair.repair_tool import RepairTool
from core.exceptions import PatternRepairError
from qualitytests.qualitytests_utils import join_resources_path, create_pattern, create_instance


class TestRepairTool:
    pattern = create_pattern()
    tp_lib: Path = join_resources_path("sample_patlib")
    template_json_dict = {
            "name": "Pattern Name",
            "description": "",
            "family": "code_pattern_LANG",
            "tags": ["sast", "LANG"],
            "instances": [
                "./IID_instance_ID_pattern_name/IID_instance_ID_pattern_name.json"
            ],
            "version": "v0.draft"
        }

    def test_init_pattern_repair0(self):
        with patch("pathlib.Path.is_file") as is_file_mock, \
            pytest.raises(PatternRepairError) as e_info:
            is_file_mock.return_value = False

            RepairTool(TestRepairTool.pattern, Path("."), Path("."))
        is_file_mock.assert_called_once()
        # logger.assert_called_once()
        assert "PatternRepair (JS - p1) No template JSON found in " in str(e_info)

    def test_init_pattern_repair1(self):
        with patch("pathlib.Path.is_file") as is_file_mock, \
            pytest.raises(PatternRepairError) as e_info:
            is_file_mock.side_effect = [True, False]

            RepairTool(TestRepairTool.pattern, Path("."), Path("."))
        is_file_mock.assert_called()
        # logger.assert_called_once()
        assert "PatternRepair (JS - p1) No schema JSON found in " in str(e_info)
    
    def test_init_pattern_repair2(self):
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            pytest.raises(PatternRepairError) as e_info:
            is_file_mock.return_value = True
            read_json_mock.return_value = {}

            RepairTool(TestRepairTool.pattern,  Path("."), Path("."))
        is_file_mock.assert_called()
        read_json_mock.assert_called_once()
        assert "PatternRepair (JS - p1) The template JSON" in str(e_info) and " is empty" in str(e_info)

    def test_copy_template(self):
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("core.repair.repair_tool.logger.info") as logger, \
            patch("shutil.copy") as copy_file_mock:

            is_file_mock.return_value = True
            read_json_mock.return_value = TestRepairTool.template_json_dict

            RepairTool(TestRepairTool.pattern,  Path("."), Path("."))._copy_template()
        
        logger.assert_called_once_with("PatternRepair (JS - p1) Copying template JSON.")
        copy_file_mock.assert_called_once()
    
    ensure_json_file_exist_testcases = [
        (False, "test_pattern_path", {"name": "test"}, False, False),
        (False, None, {"name": "test"}, True, False),
        (True, "", {"name": "test"}, False, False),
        (True, "", {"name": "test"}, False, True),
        ]

    @pytest.mark.parametrize("is_file_mock_ret, get_pattern_json_ret, read_json_ret, should_call_copy, should_rename_json", ensure_json_file_exist_testcases)
    def test_ensure_json_file_exists(self, is_file_mock_ret: bool, 
                                             get_pattern_json_ret: Path | None, 
                                             read_json_ret: dict | None, 
                                             should_call_copy: bool,
                                             should_rename_json: bool):
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("core.repair.repair_tool.logger.info"), \
            patch("core.utils.get_json_file") as get_pattern_json_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("core.utils.write_json") as write_json_mock, \
            patch("shutil.copy") as copy_template_mock, \
            patch("shutil.move") as move_mock:

            is_file_mock.return_value = True
            read_json_mock.return_value = TestRepairTool.template_json_dict

            repair_tool = RepairTool(TestRepairTool.pattern,  Path("."), Path("."))
            json_path = get_pattern_json_ret if get_pattern_json_ret else repair_tool.to_repair.json_path 
            is_file_mock.reset_mock()
            is_file_mock.return_value = is_file_mock_ret
            get_pattern_json_mock.return_value = get_pattern_json_ret
            read_json_mock.return_value = read_json_ret

            if should_rename_json:
                repair_tool.to_repair.json_path = repair_tool.to_repair.json_path.parent / "test_json.json"
                json_path = repair_tool.to_repair.json_path.parent / "test_json.json"

            repair_tool._ensure_json_file_exists()
        if should_call_copy:
            copy_template_mock.assert_called_once()
        if should_rename_json:
            move_mock.assert_called_once()
        else:
            move_mock.assert_not_called()
        is_file_mock.assert_called_once()
        read_json_mock.assert_called_with(json_path)
        write_json_mock.assert_called_once()
        expected_dict = TestRepairTool.template_json_dict
        expected_dict["name"] = "test"
        assert expected_dict == write_json_mock.call_args.args[1]

    def test_to_json1(self):
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("core.pattern.Pattern.to_dict") as to_dict_mock, \
            patch("core.utils.write_json") as write_json_mock:

            is_file_mock.return_value = True
            read_json_mock.return_value = TestRepairTool.template_json_dict

            repair_tool = RepairTool(TestRepairTool.pattern,  Path("."), Path("."))

            read_json_mock.reset_mock()
            read_json_mock.return_value = {}
            to_dict_mock.return_value = {}
            repair_tool.to_json()
        read_json_mock.assert_called_once()
        to_dict_mock.assert_called_once()
        write_json_mock.assert_not_called()
    
    def test_to_json2(self):
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("core.pattern.Pattern.to_dict") as to_dict_mock, \
            patch("core.utils.write_json") as write_json_mock:

            is_file_mock.return_value = True
            read_json_mock.return_value = TestRepairTool.template_json_dict

            repair_tool = RepairTool(TestRepairTool.pattern,  Path("."), Path("."))

            read_json_mock.reset_mock()
            read_json_mock.return_value = {"name": "test"}
            to_dict_mock.return_value = {}
            repair_tool.to_json()
        read_json_mock.assert_called_once()
        to_dict_mock.assert_called_once()
        write_json_mock.assert_called_once()

    def test_check_paths_pattern_exist_all_correct(self):
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("core.repair.repair_tool.logger.warning") as warn_logger_mock:

            is_file_mock.return_value = True
            read_json_mock.return_value = TestRepairTool.template_json_dict

            repair_tool_pattern = RepairTool(TestRepairTool.pattern,  Path("."), Path("."))

            repair_tool_pattern._check_paths_exists()
        warn_logger_mock.assert_not_called()
    
    def check_path_instance_exist_all_correct(self):
        test_instance = create_instance()
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("core.repair.repair_tool.logger.warning") as warn_logger_mock:

            is_file_mock.return_value = True
            read_json_mock.return_value = TestRepairTool.template_json_dict

            repair_tool_instance = RepairTool(test_instance,  Path("."), Path("."))

            repair_tool_instance._check_paths_exists()
        warn_logger_mock.assert_not_called()
    
    def check_path_instance_exist_non_correct(self):
        test_instance = create_instance()
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("pathlib.Path.exists") as exist_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("core.repair.repair_tool.logger.warning") as warn_logger_mock:

            is_file_mock.return_value = True
            read_json_mock.return_value = TestRepairTool.template_json_dict
            exist_mock.return_value = False

            repair_tool_instance = RepairTool(test_instance,  Path("."), Path("."))

            repair_tool_instance._check_paths_exists()
        warn_logger_mock.assert_called()
        assert test_instance.code_path is None
        assert test_instance.expectation_sink_file is None
        assert test_instance.expectation_source_file is None
        assert test_instance.compile_binary is None
        assert test_instance.discovery_rule is None
        
        

