import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from core.instance_repair import InstanceRepair
from core.exceptions import PatternRepairError
from qualitytests.qualitytests_utils import create_instance, create_pattern

class TestInstanceRepair:
    template_json_dict = {   
        "description": "",
        "code": {
            "path": "./pattern_src_code.js|php|java",
            "injection_skeleton_broken": False
        },
        "expectation": {
            "type": "xss",
            "sink_file": "./pattern_src_code.js|php|java",
            "sink_line": 0,
            "source_file": "./pattern_src_code.js|php|java",
            "source_line": 0,
            "expectation": True
        },
        "compile": {
            "binary": None,
            "instruction": None,
            "dependencies": None
        },
        "discovery": {
            "rule": "./pattern_discovery_rule.sc",
            "method": "joern",
            "rule_accuracy": "FN|FP|FPFN|Perfect",
            "notes": None
        },
        "properties": {
            "category": "S0|D1|D2|D3",
            "feature_vs_internal_api": "FEATURE",
            "input_sanitizer": False,
            "source_and_sink": False,
            "negative_test_case": False
        },
        "remediation": {
            "notes": "",
            "transformation": None,
            "modeling_rule": None
        }
    }
    def _get_instance_repair(self) -> InstanceRepair:
        test_instance = create_instance()
        test_pattern = create_pattern()
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("core.instance_repair.globals") as global_mock:
            is_file_mock.return_value = True
            read_json_mock.return_value = TestInstanceRepair.template_json_dict

            repair_tool = InstanceRepair(test_instance, test_pattern)

        global_mock.assert_called_once()
        read_json_mock.assert_called_once()
        is_file_mock.assert_called_once()
        return repair_tool            

    def test_init_instance_repair_with_wrong_language(self):
        test_instance = create_instance()
        test_instance.language = "TEST"
        test_pattern = create_pattern()
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.utils.read_json") as read_json_mock, \
            patch("core.instance_repair.logger.error") as logger_error, \
            pytest.raises(PatternRepairError) as e_info:

            is_file_mock.return_value = True
            InstanceRepair(test_instance, test_pattern)
        is_file_mock.assert_called_once()
        read_json_mock.assert_called_once()
        logger_error.assert_called_once_with("InstanceRepairTEST could not be found, maybe it is not imported?")
        assert "Could not instantiate language specific instance repair" in str(e_info)

    example_rule = """@main def main(name : String): Unit = {
            importCpg(name)
            // TODO: replace line below with your detection query
            val x2 = (name, "ID_pattern_name_i1", cpg.method.l); 
            println(x2)
            delete;
        }\n\n
        """

    discovery_rule_test_cases = [
        # one instance, remove "delete;" from scala rule and test if the right warn log message is exposed
        ([None], "", None, "delete;", 'Could not find "delete;" in'),
        # one instance, remove 2 and test if the right warn log message is provided
        ([None], "", None, "2", 'Could not find the pattern id in'),
        # one instance, dr is not in instance directory (as in samplepatlib)
        ([None], 'Changed lines in Scala rule for instance JS - p1:1:\n[\'val x1 = (name, "1_unset_element_array_iall", cpg.method.l);\', \'println(x1)\']', None, "", ""),
        # two instances, dr is not in instance directory (as in samplepatlib)
        ([None, None], 'Changed lines in Scala rule for instance JS - p1:1:\n[\'val x1 = (name, "1_unset_element_array_iall", cpg.method.l);\', \'println(x1)\']', None, "", ""),
        # two instance, dr is in instance directory
        ([None, None], 'Changed lines in Scala rule for instance JS - p1:1:\n[\'val x1 = (name, "1_unset_element_array_i1", cpg.method.l);\', \'println(x1)\']', Path("dr_rule.sc"), "", "")
    ]

    @pytest.mark.parametrize("instances, expected_info, dr_rule_path, dr_rule_replace, warn_logger_msg", discovery_rule_test_cases)
    def test_adjust_variable_number_in_discovery_works(self, instances, expected_info, dr_rule_path, dr_rule_replace, warn_logger_msg):
        test_instance_repair = self._get_instance_repair()

        test_instance_repair.pattern.instances = instances
        test_instance_repair.to_repair.path = Path("/1_unset_element_array/1_instance_1_unset_element_array")
        test_instance_repair.pattern.path = Path("/1_unset_element_array")
        if dr_rule_path:
            test_instance_repair.to_repair.discovery_rule = dr_rule_path
        dr_rule = TestInstanceRepair.example_rule.replace(dr_rule_replace, "")
        with patch("builtins.open", mock_open(read_data=dr_rule), create=True), \
            patch("core.instance_repair.logger.info") as info_logger, \
            patch("core.instance_repair.logger.warning") as warn_logger:
            test_instance_repair._adjust_variable_number_in_discovery_rule()
        
        if dr_rule_replace:
            warn_logger.assert_called_once_with(f"{warn_logger_msg} {test_instance_repair.to_repair.discovery_rule}")
            info_logger.assert_not_called()
        else:
            info_logger.assert_called_once_with(expected_info)

    def test_check_rule_accuracy_given(self):
        test_instance_repair = self._get_instance_repair()

        test_instance_repair.to_repair.discovery_rule_accuracy = "FP"
        with patch("core.instance_repair.logger.warning") as warn_logger:
            test_instance_repair._check_rule_accuracy()
        warn_logger.assert_not_called()
    
        test_instance_repair.to_repair.discovery_rule_accuracy = ""
        with patch("core.instance_repair.logger.warning") as warn_logger:
            test_instance_repair._check_rule_accuracy()
        warn_logger.assert_called_once_with("PatternRepair (JS - p1:1) Discovery rule given, but no rule accuracy.")
    
    repair_scala_rules_testcases = [
        # no discovery rule given
        (None, True, "PatternRepair (JS - p1:1) Could not find rule for JS - p1:1, skipping...", None),
        # discovery rule, but it is not a file
        (Path("discovery_rule.sc"), False, "PatternRepair (JS - p1:1) Could not find rule for JS - p1:1, skipping...", None),
        # discovery_rule, but has wrong suffix
        (Path("discovery_rule.py"), True, None, "PatternRepair (JS - p1:1) Found a rule, but it is no scala rule, don't know how to repair this, skipping..."),
        # everything is alright
        (Path("discovery_rule.sc"), True, None, None),
        ]

    @pytest.mark.parametrize("dr_rule, is_file_return, warn, info", repair_scala_rules_testcases)
    def test_repair_scala_rule(self, dr_rule, is_file_return, warn, info):
        test_instance_repair = self._get_instance_repair()
        test_instance_repair.to_repair.discovery_rule = dr_rule
        with patch("pathlib.Path.is_file") as is_file_mock, \
            patch("core.instance_repair.InstanceRepair._adjust_variable_number_in_discovery_rule") as adjust_mock, \
            patch("core.instance_repair.InstanceRepair._check_rule_accuracy") as check_rule_mock, \
            patch("core.instance_repair.logger.warning") as logger_warn_mock, \
            patch("core.instance_repair.logger.info") as logger_info_mock:
            is_file_mock.return_value = is_file_return

            test_instance_repair._repair_scala_rule()
        
        if warn:
            logger_warn_mock.assert_called_once_with(warn)
            logger_info_mock.assert_not_called()
        if info:
            logger_info_mock.assert_called_once_with(info)
            logger_warn_mock.assert_not_called()
        if not warn and not info:
            logger_info_mock.assert_not_called()
            logger_warn_mock.assert_not_called()

            check_rule_mock.assert_called_once()
            adjust_mock.assert_called_once()
    
    def test_repair(self):
        test_instance_repair = self._get_instance_repair()
        with patch("core.instance_repair.InstanceRepair._ensure_json_file_exists") as func1_mock, \
            patch("core.instance_repair.InstanceRepair._repair_scala_rule") as func2_mock, \
            patch("core.instance_repair.RepairTool.to_json") as func3_mock:
            test_instance_repair.repair()
        func1_mock.assert_called_once()
        func2_mock.assert_called_once()
        func3_mock.assert_called_once()
