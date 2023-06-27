# import json
import shutil
from os import listdir
from pathlib import Path

from core.exceptions import PatternInvalid, PatternDoesNotExists, InstanceDoesNotExists
from core.instance import Instance
from core.pattern_repair import PatternRepair
from core import utils
# from core.exceptions import LanguageTPLibDoesNotExist, PatternDoesNotExists, PatternValueError
from typing import Tuple

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))



class Pattern:
    @classmethod
    def init_from_id_and_language(cls, id: int, language: str, tp_lib_path: Path):
        return cls._init_from_id_and_language(cls(), id, language.upper(), tp_lib_path)
    
    @classmethod
    def init_from_json_file_without_pattern_id(cls, json_file_path: Path, language: str, pattern_path: Path, tp_lib_path: Path):
        return cls._init_from_json_without_id(cls(), json_file_path, language, pattern_path, tp_lib_path)

    def __init__(self) -> None:
        # metadata
        self.pattern_id = None
        self.language = None # TODO: needed?
        self.tp_lib_path = None # TODO needed?
        self.language = None
        self.pattern_path = None
        self.pattern_json_path = None

        # json fields
        self.name = None
        self.description = None
        self.family = None
        self.tags = None
        self.version = None
        self.instances = []

        # repairing tools
        self.pattern_repair = None
    
    def _assert_pattern(self):
        try:
            assert int(self.pattern_id)
            assert self.language
            assert self.tp_lib_path.is_dir()
            assert self.pattern_path.is_dir()
            assert self.pattern_json_path.is_file()
            assert self.instances and all([isinstance(instance, Instance) for instance in self.instances])
        except Exception as e:
            raise PatternInvalid(f"{self._log_prefix()}Instance Variables are not properly set. '{e}'")

    def _init_from_id_and_language(self, id: int, language: str, tp_lib_path: Path):
        self.pattern_id = id
        self.language = language.upper()
        self.tp_lib_path = tp_lib_path
        self.pattern_path = utils.get_pattern_dir_from_id(id, language, tp_lib_path)
        self._init_from_json_file(utils.get_pattern_json(self.pattern_path))
        self._assert_pattern()
        return self
    
    def _init_instances(self, instance_paths_from_json: list):
        instances = []
        for instance_json in instance_paths_from_json:
            abs_path = Path(self.pattern_path / Path(instance_json))
            if not abs_path.is_file():
                raise PatternInvalid(f"{self._log_prefix()}The instance path '{instance_json}' is not valid.")
            instances += [Instance.init_from_json_path(abs_path, self.pattern_id, self.language)]
        instances = sorted(instances, key=lambda instance: instance.instance_id)
        return instances
    
    def _init_from_json_file(self, json_file_path: Path):
        self.pattern_json_path = json_file_path
        pattern_properties = utils.read_json(self.pattern_json_path)
        if not pattern_properties:
            raise PatternInvalid("The pattern needs a valid JSON file.")
        self.name = pattern_properties["name"] if "name" in pattern_properties.keys()  else None
        self.description = pattern_properties["description"] if "description" in pattern_properties.keys() else None
        self.family = pattern_properties["family"] if "family" in pattern_properties.keys() else None
        self.tags = pattern_properties["tags"] if "tags" in pattern_properties.keys() else None
        self.version = pattern_properties["version"] if "version" in pattern_properties.keys() else None
        if "instances" in pattern_properties.keys() and pattern_properties["instances"]:
            self.instances = self._init_instances(pattern_properties["instances"])
        else:
            # Raise exception
            raise PatternInvalid(f"{self._log_prefix()}Pattern JSON file needs an 'instances' key with valid relative links.")
        return self
    
    def _init_from_json_without_id(self, json_file_path: Path, language: str, pattern_path: Path, tp_lib_path: Path):
        self.language = language.upper()
        self.pattern_path = pattern_path
        self.tp_lib_path = tp_lib_path
        self._init_from_json_file(json_file_path)
        try:
            given_id = utils.get_id_from_name(self.pattern_path.name)
        except Exception:
            given_id = None
        free_id = utils.get_next_free_pattern_id_for_language(self.language, self.tp_lib_path, given_id)
        self.pattern_id = free_id
        self._assert_pattern()
        return self
    
    def _log_prefix(self):
        return f"Pattern {self.pattern_id} ({self.language}) - "
    
    def __str__(self) -> str:
        return str(vars(self))
    
    def copy_to_tplib(self):
        # copies the pattern and all its instances into the tp_lib
        new_pattern_path = self.tp_lib_path / self.language / f'{self.pattern_id}_{self.pattern_path.name}'
        for instance in self.instances:
            instance.copy_to_tplib(new_pattern_path)
        utils.copy_dir_content(self.pattern_path, new_pattern_path)
    
    def get_instance_by_id(self, tpi_id: int) -> Instance:
        try:
            return list(filter(lambda tpi: tpi.instance_id == tpi_id, self.instances))[0]
        except KeyError:
            raise InstanceDoesNotExists(tpi_id, )
    
    def validate_for_measurement(self):
        pass

    def repair(self, soft: bool = False):
        # soft repair enforces the instances structure (and names) and updates relative instance links in pattern JSON
        self.pattern_repair = PatternRepair(self)
        self.pattern_repair.repair_pattern_json()
        if not soft:
            pass


# TODO: These functions could be obsolete, if Pattern will be used in measure, discover etc.
def get_pattern_by_pattern_id(language: str, pattern_id: int, tp_lib_dir: Path) -> Tuple[Pattern, Path]:
    pattern = Pattern.init_from_id_and_language(pattern_id, language, tp_lib_dir)
    return pattern, pattern.pattern_path


def list_tpi_paths_by_tp_id(language: str, pattern_id: int, tp_lib_dir: Path) -> list[Path]:
    try:
        pattern = Pattern.init_from_id_and_language(pattern_id, language, tp_lib_dir)
        return [instance.instance_json_path for instance in pattern.instances]
    except Exception as e:
        logger.exception(e)
        raise e
#     try:
#         pattern = Pattern.
#         p, p_dir = pattern.get_pattern_by_pattern_id(language, pattern_id, tp_lib_dir)
#         return list(map(lambda i: (tp_lib_dir / language / p_dir / i).resolve(), p.instances))
#     except:
#        
