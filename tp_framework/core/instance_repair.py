import time
import os
import re
from pathlib import Path

from core import utils
from core.exceptions import PatternRepairError

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

from core.repair_tool import RepairTool

class InstanceRepair(RepairTool):
    def __init__(self, instance, pattern: Path) -> None:
        self.pattern = pattern
        template = instance.tp_lib_path / "pattern_template" / "ID_pattern_name" / "IID_instance_ID_pattern_name" / "IID_instance_ID_pattern_name.json"
        super().__init__(instance, template)
        try:
            self.instance_repair_class = globals()[f"InstanceRepair{self.to_repair.language}"]
        except KeyError:
            logger.error(
                f"InstanceRepair{self.to_repair.language} could not be found, maybe it is not imported?"
            )
            raise PatternRepairError("Could not instantiate language specific instance repair")

    def _adjust_variable_number_in_discovery_rule(self) -> None:
        dr_path = self.to_repair.discovery_rule
        with open(dr_path, "r") as fp:
            result = fp.readlines()

        # assume, that a scala files end with
        # println(<variable_name>)
        # delete;
        try:
            println_line = result[result.index(list(filter(lambda line: "delete;" in line, result))[0]) - 1]
        except IndexError:
            logger.warning(f'Could not find "delete;" in {dr_path}')
            return
        try:
            real_number = re.search(r"println\(x(\d+)\)", println_line).group(1)
        except AttributeError:
            logger.warning(f"Could not find the pattern id in {dr_path}")
            return
        # determine the name for the rule in scala file
        # if there is more than one instance, it should be <pattern_name>_i<instance_number>
        # if this rule is for multiple patterns, it should be <pattern_name>_iall
        rule_name = (
            f'{self.pattern.path.name}_i{self.to_repair.instance_id}'
            if len(self.pattern.instances) > 1 and dr_path.parent != self.pattern.path
            else f"{self.pattern.path.name}_iall"
        )
        # make sure the number and the pattern name
        new_rule = []
        for line in result:
            new_line = line.replace(f"x{real_number}", f"x{self.pattern.pattern_id}")
            new_rule += [
                re.sub(
                    f"({self.pattern.path.name}_i(\d+|all)|ID_pattern_name_i1)",
                    rule_name,
                    new_line,
                )
            ]

        diff = [line for line in new_rule if line not in result]
        # assert False, f"{new_rule}\n\n{result}\n\n{diff}"
        if diff:
            logger.info(
                f"Changed lines in Scala rule for instance {self.to_repair}:\n{[line.strip() for line in diff]}"
            )
        with open(dr_path, "w") as fp:
            fp.writelines(new_rule)
    
    def _check_rule_accuracy(self):
        if not self.to_repair.discovery_rule_accuracy:
            logger.warning(f"{self._log_prefix()}Discovery rule given, but no rule accuracy.")

    def _repair_scala_rule(self):
        if not self.to_repair.discovery_rule or not self.to_repair.discovery_rule.is_file():
            logger.warning(f"{self._log_prefix()}Could not find rule for {self.to_repair}, skipping...")
            return
        if not self.to_repair.discovery_rule.suffix == ".sc":
            logger.info(f"{self._log_prefix()}Found a rule, but it is no scala rule, don't know how to repair this, skipping...")
            return
        self._adjust_variable_number_in_discovery_rule()
        self._check_rule_accuracy()

    def repair(self):
        # ensure JSON file exists
        self._ensure_json_file_exists()
        self._check_paths_exists()
        # language specific repair instructions
        self.instance_repair_class(self.to_repair).repair()
        # repair scala rule if exists
        self._repair_scala_rule()
        # check description
        if not self.to_repair.description:
            logger.warning(f"{self._log_prefix()}No description provided for {self.to_repair}")
        # check properties_negative_test_case vs expectation_expectation
        if self.to_repair.expectation_expectation == self.to_repair.properties_negative_test_case:
            logger.warning(f"{self._log_prefix()}Changing properites_negative_test_case, it has to be `not` expectation_expectation")
            self.to_repair.properties_negative_test_case = not self.to_repair.expectation_expectation
        # check other JSON fields
        # TODO: check if 
        self.to_json()


class InstanceRepairPHP:
    def __init__(self, instance_to_repair) -> None:
        self.instance = instance_to_repair
    
    def _log_prefix(self):
        return f"PatternRepair - PHPInstanceRepair {self.instance} "

    def _get_source_and_sink_for_file(self, path_to_file: Path) -> tuple:
        if not path_to_file:
            return (None, None)
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

    def _remove_bash_files(self):
        all_bash_files = utils.list_files(self.instance.path, ".bash")
        for file in all_bash_files:
            file.unlink()

    def _mask_line(self, input_line: str, php_file: str) -> str:
        if not php_file in input_line:
            return input_line
        line_prefix = input_line.split(os.sep)[0]
        line_suffix = input_line[input_line.rfind(".php") + 4 :]
        actual_filepath = Path(input_line.replace(line_prefix, "").replace(line_suffix, ""))
        new_path = f"{os.sep}...{os.sep}{actual_filepath.relative_to(self.instance.path.parent.parent.parent)}"
        return line_prefix + new_path + line_suffix

    def _make_opcode_from_php_file(self, php_file_path: Path) -> Path:
        # define necessary paths
        bash_file_path = php_file_path.parent / f"{php_file_path.stem}.bash"

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
        final_lines = [self._mask_line(line, str(php_file_path)) for line in result]
        with open(bash_file_path, "w") as file:
            file.writelines(final_lines)
        return Path(bash_file_path)

    def _repair_opcode(self):
        # we are radical, remove all '.bash' file and generate new ones for the '.php' files
        self._remove_bash_files()
        all_php_files = utils.list_files(self.instance.path, ".php", True)
        for file in all_php_files:
            bash_file_path = self._make_opcode_from_php_file(file)
            if not self.instance.compile_binary or not self.instance.compile_binary.is_file():
                self.instance.compile_binary = bash_file_path.relative_to(self.instance.path)
        
        all_bash_files = utils.list_files(self.instance.path, ".bash", recursive=True)
        if len(all_bash_files) != len(all_php_files):
            logger.warning(f"{self._log_prefix()}The number of php files and bash files missmatches.")

    def _repair_source_line_sink_line(self):
        _, sink_line = self._get_source_and_sink_for_file(self.instance.expectation_sink_file)
        source_line, _ = self._get_source_and_sink_for_file(self.instance.expectation_source_file)
        if not sink_line:
            logger.warning(f"{self._log_prefix()}Could not find '// sink' in sink file '{self.instance.expectation_sink_file}'")
        if not source_line:
            logger.warning(f"{self._log_prefix()}Could not find '// source' in source file '{self.instance.expectation_source_file}'")
        self.instance.expectation_sink_line = sink_line if sink_line else self.instance.expectation_sink_line
        self.instance.expectation_source_line = source_line if source_line else self.instance.expectation_source_line

    def repair(self):
        self._repair_opcode()
        self._repair_source_line_sink_line()