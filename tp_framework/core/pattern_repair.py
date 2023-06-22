import shutil
from core.exceptions import PatternRepairError
from core import utils


import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

class PatternRepair:
    def __init__(self, pattern) -> None:
        self.pattern_to_repair = pattern
        self.pattern_json_template = pattern.tp_lib_path / "pattern_template" / "ID_pattern_name" / "ID_pattern_name.json"
        if not self.pattern_json_template.is_file():
            logger.warn(f"{self._log_prefix()}Expects a template JSON file in {self.pattern_json_template}")
            raise PatternRepairError(f"No template JSON found in {self.pattern_json_template}")

    def _log_prefix(self):
        return f"PatternRepair ({self.pattern_to_repair.pattern_id} - {self.pattern_to_repair.language}) "

    def repair_pattern_json(self):
        # make sure there is a pattern JSON file
        if not self.pattern_to_repair.pattern_json_path.is_file():
            self.pattern_json_path = utils.get_pattern_json()
            if not self.pattern_json_path:
                logger.info("Copying template JSON.")
                expected_json_path = self.pattern_to_repair.pattern_path / f'{self.pattern_to_repair.name}.json'
                shutil.copy(self.pattern_json_template, expected_json_path)
        # make sure the instances are correct
        for instance in self.pattern_to_repair.instances:
            instance.repair