import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from core.instance_repair import InstanceRepairPHP
from qualitytests.qualitytests_utils import create_instance_php, join_resources_path

class TestInstanceRepairPHP:       

    def _get_instance_repair(self):
        test_instance = create_instance_php()
        return InstanceRepairPHP(test_instance)

    def test_get_source_and_sink_for_file(self):
        test_instance_php_repair = self._get_instance_repair()
        code = """<?php
            function F($a){
                static $b = 'abc'; // tarpit
                echo $b; // sink (moved out from standard skeleton)
                $b = $a;
            }
            $a = $_GET["p1"];  // source
            F($a); // print "abc"
            F('abc'); // print value of $_GET["p1"]"""
        
        with patch("builtins.open", mock_open(read_data=code), create=True):
            assert (None, None) == test_instance_php_repair._get_source_and_sink_for_file("")
            assert (None, None) == test_instance_php_repair._get_source_and_sink_for_file(None)
            assert (7, 4) == test_instance_php_repair._get_source_and_sink_for_file("code_file.php")
    
    def test_remove_bash_files(self):
        test_instance_php_repair = self._get_instance_repair()

        with patch("core.utils.list_files") as list_file_mock, \
            patch("pathlib.Path.unlink") as unlink_mock:
            list_file_mock.return_value = [Path("path_to_bash_file.bash")]
            test_instance_php_repair._remove_bash_files()
        
        list_file_mock.assert_called_once_with(test_instance_php_repair.instance.path, ".bash")
        unlink_mock.assert_called_once()
    
    def test_mask_line(self):
        test_instance_php_repair = self._get_instance_repair()
        sample_patlib = join_resources_path("sample_patlib")
        assert "line" in test_instance_php_repair._mask_line("line", "file.php")

        example_php_file_path = f"{sample_patlib}/PHP/1_static_variables/1_instance_1_static_variables/1_instance_1_static_variables.php"
        example_line_to_mask = f"     ;{example_php_file_path}:1-11"
        
        expected_masked_line = f"     ;/.../PHP/1_static_variables/1_instance_1_static_variables/1_instance_1_static_variables.php:1-11"
        assert expected_masked_line == test_instance_php_repair._mask_line(example_line_to_mask, example_php_file_path)


    def test_make_opcode_from_php_file(self):
        test_instance_php_repair = self._get_instance_repair()
        expected = test_instance_php_repair.instance.code_path.parent / "1_instance_1_static_variables.bash"
        
        with patch("os.utime") as utime_mock, \
            patch("os.system") as system_mock, \
            patch("builtins.open", mock_open(read_data="some data"), create=True), \
            patch("core.instance_repair.InstanceRepairPHP._mask_line") as mask_line_mock:
            actual = test_instance_php_repair._make_opcode_from_php_file(test_instance_php_repair.instance.code_path)
        
        assert expected == actual
        utime_mock.assert_called_once()
        system_mock.assert_called_once_with(f"php -d zend_extension=opcache -d opcache.enable_cli=1 -d opcache.opt_debug_level=0x10000 --syntax-check {test_instance_php_repair.instance.code_path} 2> {expected} 1>/dev/null")
        mask_line_mock.assert_called_once()
    
    def test_repair_opcode(self):
        test_instance_php_repair = self._get_instance_repair()
        with patch("core.instance_repair.InstanceRepairPHP._remove_bash_files") as bash_file_remove_mock, \
            patch("core.instance_repair.InstanceRepairPHP._make_opcode_from_php_file") as make_opcode_mock, \
            patch("core.utils.list_files") as list_files_mock:
            
            list_files_mock.return_value = ["file1"]

            test_instance_php_repair._repair_opcode()
        bash_file_remove_mock.assert_called_once()
        make_opcode_mock.assert_called_once()
        list_files_mock.assert_called()
    
    repair_source_sink_testcases = [
        ((None, None), True, 99, 99),
        ((1, None), True, 1, 99),
        ((None, 1), True, 99, 1),
        ((42, 24), False, 42, 24)
    ]

    @pytest.mark.parametrize("source_sink_ret, warning, exp_source, exp_sink", repair_source_sink_testcases)
    def test_repair_source_line_sink_line(self, source_sink_ret, warning, exp_source, exp_sink):
        test_instance_php_repair = self._get_instance_repair()
        expected_file = test_instance_php_repair.instance.expectation_sink_file
        test_instance_php_repair.instance.expectation_sink_line = 99
        test_instance_php_repair.instance.expectation_source_line = 99
        with patch("core.instance_repair.InstanceRepairPHP._get_source_and_sink_for_file") as source_sink_mock, \
            patch("core.instance_repair.logger.warning") as warn_logger:

            source_sink_mock.return_value = source_sink_ret
            test_instance_php_repair._repair_source_line_sink_line()
        
        source_sink_mock.assert_called_with(expected_file)
        if warning:
            warn_logger.assert_called()

        assert exp_source == test_instance_php_repair.instance.expectation_source_line
        assert exp_sink == test_instance_php_repair.instance.expectation_sink_line
