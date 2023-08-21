from pathlib import Path
from typing import Tuple

from core.exceptions import PatternInvalid, AddPatternError, InstanceDoesNotExists
from core.instance import Instance

from core import utils
from core.repair.pattern_repair import PatternRepair
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
        self.language = None
        self.tp_lib_path = None
        self.language = None
        self.path = None
        self.json_path = None

        # json fields
        self.name = None
        self.description = None
        self.family = None
        self.tags = None
        self.version = None
        self.instances = []
    
    def __str__(self) -> str:
        return f"{self.language} - p{self.pattern_id}"
    
    def _assert_pattern(self):
        try:
            assert int(self.pattern_id)
            assert self.language
            assert self.tp_lib_path.is_dir()
            assert self.path.is_dir()
            assert self.json_path.is_file()
            assert self.instances and all([isinstance(instance, Instance) for instance in self.instances])
        except Exception as e:
            raise PatternInvalid(f"{self._log_prefix()}Instance Variables are not properly set. '{e}'")

    def _init_from_id_and_language(self, id: int, language: str, tp_lib_path: Path):
        self.pattern_id = id
        self.language = language.upper()
        self.tp_lib_path = tp_lib_path
        self.path = utils.get_pattern_dir_from_id(id, language, tp_lib_path)
        self._init_from_json_file(utils.get_json_file(self.path))
        self._assert_pattern()
        return self
    
    def _init_instances(self, instance_paths_from_json: list):
        instances = []
        for instance_json in instance_paths_from_json:
            abs_path = Path(self.path / Path(instance_json))
            if not abs_path.is_file():
                raise PatternInvalid(f"{self._log_prefix()}The instance path '{instance_json}' is not valid.")
            try:
                instances += [Instance.init_from_json_path(abs_path, self.pattern_id, self.language, self.tp_lib_path)]
            except Exception as e:
                raise PatternInvalid(f"{self._log_prefix()}Could not instantiate instance, due to '{e}'")
        return instances
    
    def _init_from_json_file(self, json_file_path: Path):
        if not json_file_path:
            raise PatternInvalid(f"The provided JSON Path is not valid '{json_file_path}'")
        self.json_path = json_file_path
        pattern_properties = utils.read_json(self.json_path)
        if not pattern_properties:
            raise PatternInvalid("The pattern needs a valid JSON file.")
        self.name = pattern_properties["name"] if "name" in pattern_properties.keys()  else None
        self.description = pattern_properties["description"] if "description" in pattern_properties.keys() else None
        self.family = pattern_properties["family"] if "family" in pattern_properties.keys() else None
        self.tags = pattern_properties["tags"] if "tags" in pattern_properties.keys() else None
        self.version = pattern_properties["version"] if "version" in pattern_properties.keys() else None
        if "instances" in pattern_properties.keys() and pattern_properties["instances"]:
            self.instances = self._init_instances(pattern_properties["instances"])
            self._sort_instances()
        else:
            # Raise exception
            raise PatternInvalid(f"{self._log_prefix()}Pattern JSON file needs an 'instances' key with valid relative links.")
        return self
    
    def _init_from_json_without_id(self, json_file_path: Path, language: str, pattern_path: Path, tp_lib_path: Path):
        self.language = language.upper()
        self.path = pattern_path
        self.tp_lib_path = tp_lib_path
        self._init_from_json_file(json_file_path)
        try:
            given_id = utils.get_id_from_name(self.path.name)
        except Exception:
            given_id = None
        free_id = utils.get_next_free_pattern_id_for_language(self.language, self.tp_lib_path, given_id)
        self.pattern_id = free_id
        self._assert_pattern()
        return self
    
    def _log_prefix(self):
        return f"Pattern {self.pattern_id} ({self.language}) - "
    
    def _sort_instances(self):
        self.instances = sorted(self.instances, key=lambda instance: instance.instance_id)
    
    def copy_to_tplib(self):
        # copies the pattern and all its instances into the tp_lib
        # try to get the id from the name:
        given_id = None
        try:
            given_id = utils.get_id_from_name(self.path.name)
        except (KeyError, ValueError):
            # if we can't get an id from the name, we don't care, we just set a new id
            pass
        # if the given id is not the id, the algorithm identified, give it a new id
        pattern_name = f'{self.pattern_id}_{self.path.name}' if given_id != self.pattern_id else self.path.name
        new_pattern_path = self.tp_lib_path / self.language / pattern_name
        for instance in self.instances:
            instance.copy_to_tplib(new_pattern_path)
        try:
            utils.copy_dir_content(self.path, new_pattern_path)
        except Exception as e:
            raise AddPatternError(e)
        self.path = new_pattern_path
    
    def get_instance_by_id(self, tpi_id: int) -> Instance:
        try:
            return list(filter(lambda tpi: tpi.instance_id == tpi_id, self.instances))[0]
        except IndexError:
            raise InstanceDoesNotExists(tpi_id, "")

    def get_description(self) -> Tuple[bool, str]:
        if self.description and " " not in self.description and Path(self.path / self.description).resolve().is_file():
            with open(Path(self.path / self.description).resolve(), "r") as desc_file:
                return True, "".join(desc_file.readlines()).strip()
        else:
            return False, self.description.strip() if self.description else ""

    def repair(self, should_include_readme: bool, 
               discovery_rule_results: Path = None,
               measurement_results: Path = None,
               masking_file: Path = None,):
        PatternRepair(self).repair(self)
        if should_include_readme:
            from core.repair.readme_generator import READMEGenerator
            readme = READMEGenerator(pattern=self, discovery_rule_results=discovery_rule_results, 
                            measurement_results=measurement_results,
                            masking_file=masking_file).generate_README()
            path_to_readme = self.path  / "README.md"
            with open(path_to_readme, "w") as readme_file:
                readme_file.write(readme)
    
    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "family": self.family,
            "tags": self.tags,
            "instances": [utils.get_relative_paths(i.json_path, self.path) for i in self.instances],
            "version": self.version
        }
