import shutil
from pathlib import Path
from copy import deepcopy
from jsonschema import validate

from core.exceptions import PatternRepairError
from core import utils


import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

class RepairTool:
    def __init__(self, to_repair, template_json_file: Path, schema_file: Path) -> None:
        self.to_repair = to_repair
        self.json_template = template_json_file
        self.schema_dict = schema_file
        if not self.json_template.is_file():
            raise PatternRepairError(f"{self._log_prefix()}No template JSON found in {self.json_template}")
        if not schema_file.is_file():
            raise PatternRepairError(f"{self._log_prefix()}No schema JSON found in {schema_file}")
        try:
            self.template_dict = utils.read_json(self.json_template)
        except Exception:
            raise PatternRepairError(f"{self._log_prefix()}The template JSON file {self.json_template} is corrupt, please check")
        if not self.template_dict:
            raise PatternRepairError(f"{self._log_prefix()}The template JSON {self.json_template} is empty")
        try:
            self.schema_dict = utils.read_json(schema_file)
        except Exception:
            raise PatternRepairError(f"{self._log_prefix()}The schema JSON file {schema_file} is corrupt, please check")

    def _log_prefix(self):
        return f"PatternRepair ({self.to_repair}) "

    def _copy_template(self):
        logger.info(f"{self._log_prefix()}Copying template JSON.")
        expected_json_path = self.to_repair.path / f'{self.to_repair.path.name}.json'
        shutil.copy(self.json_template, expected_json_path)
        self.to_repair.json_path = expected_json_path
        return expected_json_path

    def _ensure_json_file_exists(self):
        to_repair_json_path = self.to_repair.json_path
        # check if json path is a file
        if not to_repair_json_path.is_file():
            # try to get the file, if not possible copy the template
            to_repair_json_path = utils.get_json_file()
            if not to_repair_json_path:
                to_repair_json_path = self._copy_template()
        # read the given file to check if there are errors or keys missing
        pattern_dict = {}
        try:
            org_pattern_dict = utils.read_json(to_repair_json_path)
        except Exception:
            self._copy_template()
            org_pattern_dict = utils.read_json(self.to_repair.json_path)
        
        pattern_dict = deepcopy(org_pattern_dict)
        # check for missing keys
        missing_keys_in_pattern_dict = set(self.template_dict.keys()) - set(pattern_dict.keys())
        for key in missing_keys_in_pattern_dict:
            pattern_dict[key] = self.template_dict[key]
        
        if pattern_dict != org_pattern_dict:
            utils.write_json(self.to_repair.json_path, pattern_dict)

        # rename the JSON file to the expected format
        expected_json_name = f"{self.to_repair.path.name}.json"
        actual_name = self.to_repair.json_path.name

        if expected_json_name != actual_name:
            new_path = self.to_repair.path / expected_json_name
            shutil.move(self.to_repair.json_path, new_path)
            self.to_repair.json_path = new_path

    def _check_paths_exists(self):
        for k, v in vars(self.to_repair).items():
            if isinstance(v, Path):
                attr = getattr(self.to_repair, k)
                if not attr.exists():
                    logger.warning(f"{self._log_prefix()}Could not find path {v}")
                    setattr(self.to_repair, k, None)

    def _validate_against_schema(self):
        repaired_dict = self.to_repair.to_dict()
        try:
            validate(instance=repaired_dict, schema=self.schema_dict)
        except Exception as e:
            msg = utils.get_exception_message(e)
            logger.error(f"{self._log_prefix()}Validating against schema failed: {msg}")

    def repair(self):
        raise NotImplementedError()

    def to_json(self):
        repaired_dict = self.to_repair.to_dict()

        original_dict = utils.read_json(self.to_repair.json_path)
        if repaired_dict != original_dict:
            utils.write_json(self.to_repair.json_path, repaired_dict)
