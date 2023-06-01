import os
import logging

from pattern_repair.instance_repair import InstanceRepair
from pattern_repair.PHP.generate_opcode import PHPOpcodeGenerator
from pattern_repair.utils import *


class InstanceRepairPHP(InstanceRepair):
    def _get_source_and_sink_for_file(self, path_to_file: str) -> tuple:
        """Looks for '// source' and '// sink' in a file and returns the line numbers of these lines (index starting at 1)

        Args:
            path_to_file (str): path to the file source and sink should be found in.

        Returns:
            tuple: (source_line, sink_line) if one does not exists, it returns None for that.
        """
        with open(path_to_file, "r") as fp:
            file_lines = fp.readlines()
        sink = None
        source = None
        for idx, line in enumerate(file_lines):
            if "// sink" in line:
                sink = idx + 1
            if "// source" in line:
                source = idx + 1
        return (source, sink)

    def _repair_json_field_with_path(
        self, instance_dict: dict, file_ending: str, keyword1: str, keyword2: str
    ) -> dict:
        """Checks if the path in the JSON, identified by keyword1 and keyword2 is path to a valid file.

        Args:
            instance_dict (dict): Dict of instance
            file_ending (str): fileending of the wanted file
            keyword1 (str): Keyword for first level in `instance_dict`
            keyword2 (str): Keyword in second level in `instance_dict`

        Returns:
            dict: Dict of instance
        """
        if not instance_dict[keyword1][keyword2]:
            logger.warning(f"Instance dict at {keyword1}:{keyword2} is not defined.")
            return instance_dict
        # get the expected path and check if it is represented
        expected_path = f".{os.sep}{self.instance_name}.{file_ending}"
        abs_expected_path = os.path.abspath(
            os.path.join(self.instance_path, expected_path)
        )
        if os.path.isfile(abs_expected_path):
            instance_dict[keyword1][keyword2] = expected_path
        else:
            # check if the path inserted in the field is actually valid
            if os.path.isfile(
                os.path.join(self.instance_path, instance_dict[keyword1][keyword2])
            ):
                return instance_dict
            logger.warning(
                f"Could not verify {file_ending} filepath for instance {self.instance_name}"
            )
        return instance_dict

    def _repair_json_expectation(self, instance_dict: dict) -> dict:
        """Corrects 'expectation:source_file', 'expectation:sink_file', 'expectation:source_line', 'expectation:sink_line'

        Args:
            instance_dict (dict): Dict of instance

        Returns:
            dict: Dict of instance
        """
        # get paths from the JSON file
        path_to_source_file = instance_dict["expectation"]["source_file"]
        abs_path_to_source_file = os.path.join(self.instance_path, path_to_source_file)
        path_to_sink_file = instance_dict["expectation"]["sink_file"]
        abs_path_to_sink_file = os.path.join(self.instance_path, path_to_sink_file)
        path_to_php_file = instance_dict["code"]["path"]
        abs_path_to_php_file = os.path.join(self.instance_path, path_to_php_file)

        if not path_to_php_file or not os.path.isfile(abs_path_to_php_file):
            logging.warning(f'Could not verify "expectation" for {self.instance_name}')
            return instance_dict

        if not os.path.isfile(abs_path_to_sink_file):
            abs_path_to_sink_file = abs_path_to_php_file
            path_to_sink_file = path_to_php_file
            logging.info(f"Changing sink file path to {path_to_php_file}")
        if not os.path.isfile(abs_path_to_source_file):
            abs_path_to_source_file = abs_path_to_php_file
            path_to_source_file = path_to_php_file
            logging.info(f"Changing source file path to {path_to_php_file}")
        source0, sink0 = self._get_source_and_sink_for_file(abs_path_to_sink_file)
        source1, sink1 = self._get_source_and_sink_for_file(abs_path_to_source_file)

        # set values in instance dict
        instance_dict["expectation"]["source_file"] = path_to_source_file
        instance_dict["expectation"]["source_line"] = source0 if source0 else source1
        instance_dict["expectation"]["sink_file"] = path_to_sink_file
        instance_dict["expectation"]["sink_line"] = sink0 if sink0 else sink1
        if not (bool(source0) or bool(source1)):
            logging.warning(f"Could not verify source files for {self.instance_name}")
        if not (bool(sink0) or bool(sink1)):
            logging.warning(f"Could not verify sink files for {self.instance_name}")
        return instance_dict

    def _repair_opcode(self):
        """Generates opcode and checks if it is empty."""
        bash_file_paths = PHPOpcodeGenerator(
            self.instance_path, self.path_to_testability_patterns
        ).generate_opcode_for_pattern_instance()
        for bash_file_path in bash_file_paths:
            if not bash_file_path or not os.stat(bash_file_path).st_size:
                logging.warning(f"Bash file {bash_file_path} is empty")

    def _repair_instance_json(self) -> None:
        """Repairs JSON of instance"""
        # make sure file exists and has all the right fields
        super().repair_instance_json()
        instance_dict = read_json(self.instance_json_file)
        # make sure bash filepath is correct
        instance_dict = self._repair_json_field_with_path(
            instance_dict, "bash", "compile", "binary"
        )
        # make sure PHP filepath is correct
        instance_dict = self._repair_json_field_with_path(
            instance_dict, "php", "code", "path"
        )
        # make sure discovery filepath is correct
        instance_dict = self._repair_json_field_with_path(
            instance_dict, "sc", "discovery", "rule"
        )
        # make sure expectations is correct
        instance_dict = self._repair_json_expectation(instance_dict)
        write_json(self.instance_json_file, instance_dict)

    def _repair_num_files(self) -> None:
        """Checks how many php and bash files are there."""
        all_bash_files = get_files_with_ending(self.instance_path, ".bash")
        all_php_files = get_files_with_ending(self.instance_path, ".php")
        if len(all_bash_files) != len(all_php_files):
            logging.warning(
                f"Expected same number of .bash and .php files, but got {len(all_php_files)} PHP files and {len(all_bash_files)} BASH files"
            )

    def repair(self):
        super().repair_instance_json()
        super().repair()
        self._repair_opcode()
        self._repair_instance_json()
