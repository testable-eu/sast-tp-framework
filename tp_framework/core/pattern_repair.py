from pathlib import Path
from copy import deepcopy

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))


from core.exceptions import InstanceInvalid
from core.instance import Instance
from core.repair_tool import RepairTool
from core import utils

class PatternRepair(RepairTool):
    def __init__(self, pattern) -> None:
        json_template = pattern.tp_lib_path / "pattern_template" / "ID_pattern_name" / "ID_pattern_name.json"
        super().__init__(pattern, json_template)

    def _complete_instances(self):
        # list pattern directory and try to find all instances
        potential_instances = utils.list_directories(self.to_repair.path)
        actual_instances = [i.path for i in self.to_repair.instances]

        # potentially all dirs, that are in the symmetric_difference of potential_instances and actual_instances could be missing instances
        missing_instances = set(potential_instances) ^ set(actual_instances)
        for m_instance in missing_instances:
            instance_json = utils.get_json_file(m_instance)
            if instance_json:
                # if there is a JSON file, try to instantiate an Instance from it
                try:
                    new_instance = Instance.init_from_json_path(instance_json, self.to_repair.pattern_id, self.to_repair.language, self.to_repair.tp_lib_path)
                except Exception:
                    logger.warn(f"Found potential instance JSON at {instance_json}, but cannot initialize instance.")
                    continue
                self.to_repair.instances += [new_instance]
        self.to_repair._sort_instances()
        # check if instances are named after naming scheme {instance_id}_instance_{pattern_name} 
        for instance in self.to_repair.instances:
            expected_name = f"{instance.instance_id}_instance_{self.to_repair.path.name}"
            actual_name = instance.name
            if expected_name != actual_name:
                new_path = instance.path.parent / expected_name
                instance.set_new_instance_path(new_path)

    def _repair_name(self):
        self.to_repair.name = " ".join([w.title() for w in self.to_repair.path.name.split("_")[1:]])
        if not self.to_repair.name:
            logger.warn(f"{self._log_prefix()}The name of this pattern is weird.")

    def _repair_description(self):
        is_file, description = self.to_repair.get_description()
        if not description:
            logger.warn(f"{self._log_prefix()}Could not find description.")
            return
        
        # check if description is in JSON and is longer than 140 symbols
        if not is_file and len(description) > 140:
            # description is a bit to long, put it into file
            path_to_new_description_file = self.to_repair.path / "docs" / "description.md"
            path_to_new_description_file.parent.mkdir(parents=True, exist_ok=True)
            with open(path_to_new_description_file, "w") as desc_file:
                desc_file.write(description)
            logger.info(f"{self._log_prefix()}Moving description into ./docs/description.md")
            self.to_repair.description = utils.get_relative_paths(path_to_new_description_file, self.to_repair.path)
        
        # check if instances have the same description
        for instance in self.to_repair.instances:
            if description == instance.get_description()[1].strip():
                logger.info(f"{self._log_prefix()}Instance description is the same as pattern description, removing instance description.")
                instance.description = ""

    def _repair_tags(self):
        if not self.to_repair.tags or set(self.to_repair.tags) == set(self.template_dict["tags"]):
            # default tags have not been changed, or there are no tags, set default tags.
            self.to_repair.tags = ["sast", self.to_repair.language]
        self.to_repair.tags = [t.upper() if t.upper() == self.to_repair.language else t for t in self.to_repair.tags]
        self.to_repair.tags = sorted(self.to_repair.tags, key=lambda x: x.lower())

    def repair(self, pattern):
        # make sure, that the JSON file exist
        self._ensure_json_file_exists()
        self._check_paths_exists()
        # get all instances
        self._complete_instances()
        # repair instances
        for instance in self.to_repair.instances:
            instance.repair(pattern)
        # fix name
        self._repair_name()
        self._repair_description()
        self._repair_tags()

        # write to json
        self.to_json()
