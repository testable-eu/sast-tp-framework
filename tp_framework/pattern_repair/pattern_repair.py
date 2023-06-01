import os
import shutil
import logging

from copy import deepcopy
from pathlib import Path

from pattern_repair.utils import (
    assert_pattern_valid,
    repair_keys_of_json,
    get_template_pattern_json_path,
    read_json,
    write_json,
    compare_dicts,
    get_files_with_ending,
    list_instances_jsons,
)
from pattern_repair.README_generator import READMEGenerator
from pattern_repair.PHP.instance_repair_php import InstanceRepairPHP

from core.utils import check_lang_tp_lib_path, get_id_from_name
from core import loggermgr

logger = logging.getLogger(loggermgr.logger_name(__name__))


class PatternRepair:
    def __init__(
        self,
        path_to_pattern: Path,
        language: str,
        tp_lib_path: Path,
        discovery_rule_results: str = "",
        masking_file: str = "",
        all_measurement_results: str = "",
    ) -> None:
        check_lang_tp_lib_path(Path(os.path.join(tp_lib_path, language.upper())))
        assert_pattern_valid(path_to_pattern)

        # user defined constants
        self.pattern_path = path_to_pattern
        self.pattern_name = os.path.basename(self.pattern_path)
        self.pattern_id = get_id_from_name(self.pattern_name)
        self.language = language
        self.pattern_json_file = None
        self.discovery_rule_results = discovery_rule_results
        self.masking_file = masking_file
        self.all_measurement_results = all_measurement_results
        self.tp_lib_path = tp_lib_path

        # get repair for specific language
        try:
            self.instance_repair_class = globals()[f"InstanceRepair{language.upper()}"]
        except KeyError:
            logger.error(
                f"InstanceRepair{language.upper()} could not be found, maybe it is not imported?"
            )
            exit(1)

    def _find_instances_json(self) -> list:
        """Gets all pattern instance jsons as relative paths

        Returns:
            list: list of relative paths to JSON files.
        """
        #
        pattern_instances = list_instances_jsons(self.pattern_path)
        if not pattern_instances:
            return []
        # get the relative path for instances
        pattern_instances_rel_path = [
            f".{os.sep}{os.path.relpath(str(pattern_instance_path), self.pattern_path)}"
            for pattern_instance_path in pattern_instances
        ]
        return pattern_instances_rel_path

    def _repair_documentation(self) -> None:
        """Makes sure, the pattern description is in a `./docs/description.md` and the field in the JSON file points to that markdown file."""
        # make sure ./docs/description.md exists
        docs_directory = os.path.join(self.pattern_path, "docs")
        description_file_path = os.path.join(docs_directory, "description.md")
        os.makedirs(docs_directory, exist_ok=True)
        open(description_file_path, "a").close()

        # check out the "description" field in the pattern JSON file
        json_dict = read_json(self.pattern_json_file)
        description_in_json = json_dict["description"]
        rel_path_to_description = (
            f".{os.sep}{os.path.relpath(description_file_path, self.pattern_path)}"
        )
        if rel_path_to_description == description_in_json:
            # the description_in_json is already the right path
            if not os.stat(description_file_path).st_size:
                logger.info(f"Description for {self.pattern_name} is missing")
            return

        # set the description field point to ./docs/description.md
        json_dict["description"] = rel_path_to_description
        original_description = []
        with open(description_file_path, "r") as fp:
            original_description = fp.readlines()
        original_description += [description_in_json]
        with open(description_file_path, "w") as fp:
            fp.write("\n".join(original_description))
        write_json(self.pattern_json_file, json_dict)
        if description_in_json:
            logger.info(f"Changed {description_file_path} in pattern JSON")
        else:
            logger.info(f"Description for Pattern {self.pattern_name} is missing")

    def _repair_instances(self) -> None:
        """Repairs instances of that pattern, using the instance repair class as well."""
        all_instances = list_instances_jsons(self.pattern_path)
        if not all_instances:
            logger.error(f"Pattern {self.pattern_name} has no instances")
            exit(1)
        for instance_json in all_instances:
            self.instance_repair_class(
                self.language, self.pattern_path, instance_json, self.tp_lib_path
            ).repair()

    def _repair_pattern_json(self) -> None:
        """Repairs the JSON file of the pattern"""
        # check if pattern json file exists, if not copy the template
        pattern_json = os.path.join(self.pattern_path, f"{self.pattern_name}.json")
        self.pattern_json_file = pattern_json
        if not os.path.isfile(pattern_json):
            logger.info("Could not find Pattern JSON, copying the template")
            shutil.copy(get_template_pattern_json_path(self.tp_lib_path), pattern_json)
        repair_keys_of_json(
            self.pattern_json_file, get_template_pattern_json_path(self.tp_lib_path)
        )

        # get the content of the pattern json
        pattern_dict = read_json(pattern_json)

        # adapt the fields (name, family, tags, instances) of the pattern_dict for the fields
        new_pattern_dict = deepcopy(pattern_dict)
        new_pattern_dict["name"] = " ".join(self.pattern_name.split("_")[1:]).title()
        new_pattern_dict["family"] = f"code_pattern_{self.language.lower()}"
        if "LANG" in new_pattern_dict["tags"]:
            new_pattern_dict["tags"] = ["sast", self.language.lower()]
        new_pattern_dict["instances"] = self._find_instances_json()
        new_pattern_dict["version"] = (
            new_pattern_dict["version"] if new_pattern_dict["version"] else "v0.draft"
        )

        # compare with original dict and if something has changed write the new dict to file
        dict_diff = compare_dicts(pattern_dict, new_pattern_dict)
        if dict_diff:
            write_json(pattern_json, new_pattern_dict)
        self._repair_documentation()

    def _repair_pattern_README(self) -> None:
        """Repairs the README file of the pattern"""
        all_md_files = get_files_with_ending(self.pattern_path, ".md")
        if not len(all_md_files) == 1:
            logger.info(
                f'There are multiple or no ".md" files in pattern {self.pattern_name}'
            )
            return
        os.rename(all_md_files[0], os.path.join(self.pattern_path, "README.md"))
        pattern_measurement = os.path.join(
            self.all_measurement_results, self.pattern_name
        )
        instance_jsons = list_instances_jsons(self.pattern_path)
        new_readme = READMEGenerator(
            self.pattern_path,
            self.language,
            self.tp_lib_path,
            instance_jsons,
            self.discovery_rule_results,
            pattern_measurement,
            self.masking_file,
        ).generate_README()
        with open(os.path.join(self.pattern_path, "README.md"), "w") as file:
            file.write(new_readme)

    def repair(self, should_include_readme: bool = True):
        self._repair_pattern_json()
        self._repair_instances()
        if should_include_readme:
            self._repair_pattern_README()
