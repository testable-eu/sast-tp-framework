#!/usr/bin/env python3

"""
This script can be used to generate opcode for PHP patterns
"""
import os
import logging
import time

from pattern_repair.utils import get_files_with_ending, read_json, write_json
from core import loggermgr

logger = logging.getLogger(loggermgr.logger_name(__name__))


class PHPOpcodeGenerator:
    """This class encapsulates the opcode generation for PHP files"""

    def __init__(
        self, pattern_instance_path: str, path_to_testability_patterns: str
    ) -> None:
        self.pattern_instance_path = pattern_instance_path
        self.path_to_testability_patterns = path_to_testability_patterns

    def _adjust_json_file(self, bash_file_name):
        """Adapts the JSON file of the instance, that 'compile', 'binary' points to the new opcode file

        Args:
            bash_file_name (_type_): _description_
        """
        json_files_paths = get_files_with_ending(self.pattern_instance_path, ".json")
        if not len(json_files_paths) == 1:
            logger.error(
                f"Expected one JSON file for {self.pattern_instance_path} got {len(json_files_paths)}"
            )
            exit(1)
        result_dict = read_json(json_files_paths[0])
        result_dict["compile"][
            "binary"
        ] = f".{os.sep}{os.path.relpath(bash_file_name, self.pattern_instance_path)}"
        write_json(json_files_paths[0], result_dict)

    def _mask_line(self, input_line: str, php_file: str) -> str:
        """Should masquerades the opcode line, where the path to the php file is written.
        If `php_file` cannot be found in `input_line`, the `input_line` is returned.

        Args:
            input_line (str): any line from bash code file.
            php_file (str): path of php file.

        Returns:
            str: masked line, everything, that is before the testability pattern lib is cut with `/../`.
        """
        if not php_file in input_line:
            return input_line
        line_prefix = input_line.split(os.sep)[0]
        line_suffix = input_line[input_line.rfind(".php") + 4 :]
        actual_filepath = input_line.replace(line_prefix, "").replace(line_suffix, "")
        new_path = f"{os.sep}...{os.sep}{os.path.relpath(actual_filepath, self.path_to_testability_patterns)}"
        return line_prefix + new_path + line_suffix

    def _make_optcode_from_php_file(self, php_file_path: str) -> str:
        """Generates opcode for a php file.

        Args:
            php_file_path (str): Path to PHP file

        Returns:
            str: File path to the corresponding file containing the opcode.
        """
        # define necessary paths
        php_file_path = os.path.abspath(php_file_path)
        bash_file_path = f'{php_file_path.strip("ph")}bash'

        # opcache will only compile and cache files older than the script execution start (https://www.php.net/manual/en/function.opcache-compile-file.php)
        # therefor we have to modify the time the php file was created
        one_minute_ago = time.time() - 60
        os.utime(php_file_path, (one_minute_ago, one_minute_ago))

        # Generate the bash file
        os.system(
            f"php -d zend_extension=opcache -d opcache.enable_cli=1 -d opcache.opt_debug_level=0x10000 --syntax-check {php_file_path} 2> {bash_file_path} 1>/dev/null"
        )

        # Sanitize the opcode: on some systems, there is an error included in the bash file
        with open(bash_file_path, "r") as file:
            result = file.readlines()
        for idx, line in enumerate(result):
            if line.startswith("$_main"):
                result = result[max(idx - 1, 0) :]
                break
        # mask the path to file
        final_lines = [self._mask_line(line, php_file_path) for line in result]
        with open(bash_file_path, "w") as file:
            file.writelines(final_lines)
        return bash_file_path

    def generate_opcode_for_pattern_instance(self) -> str:
        """Generates the opcode for a pattern instance, and adjusts the JSON file accordingly.

        Returns:
            str: file path to the generated opcode.
        """
        php_files_paths = get_files_with_ending(
            self.pattern_instance_path, ".php", recursive=True
        )
        if not php_files_paths:
            logger.warning(
                f"Expected one PHP file for {self.pattern_instance_path}, found {len(php_files_paths)}"
            )
            return []
        bash_files = []
        for php_file_path in php_files_paths:
            bash_files += [self._make_optcode_from_php_file(php_file_path)]
        if len(php_files_paths) == 1:
            self._adjust_json_file(bash_files[-1])
        return bash_files
