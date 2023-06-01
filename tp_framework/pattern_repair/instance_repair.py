import logging
import os
import re
import shutil

from pattern_repair.utils import (
    assert_pattern_valid,
    repair_keys_of_json,
    read_json,
    write_json,
    list_instances_jsons,
    INSTANCE_JSON_NOT_MANDATORY_KEYS,
    get_template_instance_json_path,
    get_template_instance_discovery_rule_path,
)

from core.utils import get_id_from_name

from core import loggermgr

logger = logging.getLogger(loggermgr.logger_name(__name__))


class InstanceRepair:
    """Super class for all language specific `InstanceRepair`."""

    def __init__(
        self,
        language: str,
        path_to_pattern: str,
        instance_json_path: str,
        path_to_tp_lib: str,
    ) -> None:
        assert_pattern_valid(path_to_pattern)

        self.language = language
        self.pattern_path = path_to_pattern
        self.pattern_name = os.path.basename(self.pattern_path)
        self.pattern_id = get_id_from_name(self.pattern_name)
        self.instance_path = os.path.dirname(instance_json_path)
        self.instance_name = os.path.basename(self.instance_path)
        self.instance_json_file = instance_json_path
        self.path_to_testability_patterns = path_to_tp_lib

    def _adjust_variable_number_in_discovery_rule(
        self, path_to_discovery_file: str
    ) -> None:
        """Adjusts the scala discovery file.

        Args:
            path_to_discovery_file (str): path to discovery file
        """
        pattern_number = int(os.path.basename(self.pattern_path).split("_")[0])
        with open(path_to_discovery_file, "r") as fp:
            result = fp.readlines()

        # assume, that a scala files end with
        # println(<variable_name>)
        # delete;
        try:
            println_line = result[
                result.index(list(filter(lambda line: "delete;" in line, result))[0])
                - 1
            ]
        except IndexError:
            logger.warning(
                f'Could not find "delete;" in {os.path.relpath(path_to_discovery_file, self.instance_path)}'
            )
            return
        try:
            real_number = re.search(r"println\(x(\d+)\)", println_line).group(1)
        except AttributeError:
            logger.warning(
                f"Could not find the pattern number in {os.path.relpath(path_to_discovery_file, self.instance_path)}"
            )
            return
        # determine the name for the rule in scala file
        # if there is more than one instance, it should be <pattern_name>_i<instance_number>
        # if this rule is for multiple patterns, it should be <pattern_name>_iall
        rule_name = (
            f'{self.pattern_name.lower()}_i{self.instance_name.split("_")[0]}'
            if len(list_instances_jsons(self.pattern_path)) > 1
            and os.path.abspath(os.path.dirname(path_to_discovery_file))
            != os.path.abspath(self.pattern_path)
            else f"{self.pattern_name}_iall"
        )
        # make sure the number and the pattern name
        new_rule = []
        for line in result:
            new_line = line.replace(f"x{real_number}", f"x{pattern_number}")
            new_rule += [
                re.sub(
                    f"({self.pattern_name}_i(\d+|all)|ID_pattern_name_i1)",
                    rule_name,
                    new_line,
                )
            ]

        diff = [line for line in new_rule if line not in result]
        if diff:
            logger.info(
                f"Changed lines in Scala rule for instance {self.instance_name}:\n{[line.strip() for line in diff]}"
            )
        with open(path_to_discovery_file, "w") as fp:
            fp.writelines(new_rule)

    def _check_rule_accuracy(self):
        """Checks that there is a rule accuracy given if there is a rule given"""
        instance_dict = read_json(self.instance_json_file)
        if (
            instance_dict["discovery"]["rule"]
            and not instance_dict["discovery"]["rule_accuracy"]
        ):
            logger.warning(
                f"There is a rule, but no rule accuracy given for {self.instance_name}"
            )

    def _repair_description(self) -> None:
        """Checks if 'description' is given in an instance dict, removes the key, when it is empty."""
        instance_dict = read_json(self.instance_json_file)
        if "description" not in instance_dict.keys():
            logger.warning(
                f"Instance description for {self.instance_name} does not exist."
            )
            return
        if not instance_dict["description"]:
            instance_dict.pop("description")
            logger.warning(
                f"Instance description for {self.instance_name} is empty, deleting it."
            )
            write_json(self.instance_json_file, instance_dict)

    def _repair_discovery_rule(self) -> None:
        """Repairs the discovery rule of a pattern instance"""
        instance_dict = read_json(self.instance_json_file)
        path_to_discovery_rule = os.path.join(
            self.instance_path, f"{self.instance_name}.sc"
        )
        expected_file = (
            f".{os.sep}{os.path.relpath(path_to_discovery_rule, self.instance_path)}"
        )
        real = (
            instance_dict["discovery"]["rule"]
            if instance_dict["discovery"]["rule"]
            else ""
        )
        # check if there is already a path to a discovery rule given
        if os.path.isfile(os.path.join(self.instance_path, real)):
            if expected_file == real:
                # the file path is correct, just check the structure of the file
                self._repair_discovery_rule_structure(
                    os.path.join(self.instance_path, real)
                )
                return
            else:
                real_path = os.path.join(self.instance_path, real)
                if os.path.isfile(real_path):
                    self._repair_discovery_rule_structure(real_path)
                    return
                # there is a discovery rule, but not a scala file
                logger.warning(
                    f"No scala discovery rule found for {self.instance_path}"
                )
                return
        # given value is not a real file, so check if there is nevertheless a discovery rule
        if not os.path.isfile(path_to_discovery_rule):
            logger.info(
                f"Could not find discovery rule for {self.instance_name}, added sc file"
            )
            logger.warning(f"Please adjust discovery rule of {self.instance_name}")
            shutil.copy(
                get_template_instance_discovery_rule_path(
                    self.path_to_testability_patterns
                ),
                path_to_discovery_rule,
            )
        # adapt scala file
        self._repair_discovery_rule_structure(path_to_discovery_rule)
        # adapt JSON file
        instance_dict["discovery"]["rule"] = expected_file
        write_json(self.instance_json_file, instance_dict)

    def _repair_discovery_rule_structure(self, path_to_discovery_file: str) -> None:
        self._adjust_variable_number_in_discovery_rule(path_to_discovery_file)
        self._check_rule_accuracy()

    def repair_instance_json(self) -> None:
        """Repairs the instance JSON of the pattern"""
        if not os.path.isfile(self.instance_json_file):
            logger.info(
                f"Could not find instance JSON for {self.instance_name}, copying template"
            )
            shutil.copy(
                get_template_instance_json_path(self.path_to_testability_patterns),
                self.instance_json_file,
            )
        repair_keys_of_json(
            self.instance_json_file,
            get_template_instance_json_path(self.path_to_testability_patterns),
            INSTANCE_JSON_NOT_MANDATORY_KEYS,
        )
        self._repair_description()

    def repair(self) -> str:
        self._repair_discovery_rule()
