import csv
import os
from datetime import datetime
from platform import system

from importlib import import_module
from pathlib import Path
from typing import Tuple, Dict
import yaml

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

import config
from core import pattern
from core.exceptions import PatternDoesNotExists, LanguageTPLibDoesNotExist, TPLibDoesNotExist, InvalidSastTools, \
    DiscoveryMethodNotSupported, TargetDirDoesNotExist, InvalidSastTool
from core import errors


def is_windows():
    return system() == "Windows"


def list_pattern_paths_for_language(language: str, tp_lib_dir: Path) -> list[Path]:
    all_pattern_dirs_by_lang: Path = tp_lib_dir / language
    if not all_pattern_dirs_by_lang.is_dir():
        raise LanguageTPLibDoesNotExist
    return list(all_pattern_dirs_by_lang.iterdir())


def list_pattern_instances_by_pattern_id(language: str, pattern_id: int, tp_lib_dir: Path) -> list[Path]:
    try:
        p, p_dir = pattern.get_pattern_by_pattern_id(language, pattern_id, tp_lib_dir)
        return list(map(lambda i: (tp_lib_dir / language / p_dir / i).resolve(), p.instances))
    except:
        raise PatternDoesNotExists(pattern_id)


def get_pattern_dir_from_id(pattern_id: int, language: str, tp_lib_dir: Path) -> Path:
    tp_lib_dir_lang_dir: Path = tp_lib_dir / language
    if tp_lib_dir_lang_dir.is_dir():
        return list(filter(lambda p: int(p.name.split("_")[0]) == pattern_id, tp_lib_dir_lang_dir.iterdir()))[0]
    else:
        raise PatternDoesNotExists(pattern_id)


# def get_or_create_language_dir(language: str, tp_lib_dir: Path) -> Path:
#     tp_lib_for_lang: Path = tp_lib_dir / language
#     tp_lib_for_lang.mkdir(parents=True, exist_ok=True)
#     return tp_lib_for_lang


def get_or_create_pattern_dir(language: str, pattern_id: int, pattern_name: str, tp_lib_dir: Path) -> Path:
    pattern_dir = tp_lib_dir / language / get_pattern_dir_name_from_name(pattern_name, pattern_id)
    pattern_dir.mkdir(parents=True, exist_ok=True)
    return pattern_dir


def get_pattern_dir_name_from_name(name: str, pattern_id: int) -> str:
    return "{}_{}".format(pattern_id, name.lower().replace(" ", "_"))


def get_instance_dir_name_from_pattern(name: str, pattern_id: int, instance_id: int) -> str:
    return "{}_instance_{}_{}".format(instance_id, pattern_id, name.lower().replace(" ", "_"))


def get_id_from_name(name: str) -> int:
    return int(name.split("_")[0])


def get_class_from_str(class_str: str) -> object:
    try:
        module_path, class_name = class_str.rsplit('.', 1)
        module = import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(class_str)


def get_measurement_dir_for_language(tp_lib_dir: Path, language: str):
    return Path(tp_lib_dir / config.MEASUREMENT_REL_DIR / language)


def get_last_measurement_for_pattern_instance(meas_inst_dir: Path) -> Path:
    measurements: list[Path] = list(meas_inst_dir.iterdir())
    sorted_meas: list[Tuple[datetime, Path]] = list(sorted(
        zip(
            map(lambda m: datetime.strptime(m.name.split(".")[0].split("measurement-")[1], "%Y-%m-%d_%H-%M-%S"),
                measurements),
            measurements), key=lambda k: k[0]))
    return sorted_meas[-1][1]


# Useful for some SAST tools that accepts a zip file of the source code to scan
def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file),
                       os.path.relpath(os.path.join(root, file),
                                       os.path.join(path, '..')))


################################################################################
# TODO (LC): are these instance related?
#
def get_path_or_none(p: str) -> Path | None:
    if p is not None:
        return Path(p)
    return p


def get_enum_value_or_none(enum) -> str | None:
    try:
        return enum.value
    except AttributeError:
        return None


def get_relative_path_str_or_none(path) -> str | None:
    if path is not None:
        return f"./{path}"
    return None


def get_from_dict(d, k1, k2):
    return d.get(k1, {}).get(k2, None)


################################################################################
# Discovery
#

def get_discovery_rule_ext(discovery_method: str):
    try:
        return config.DISCOVERY_RULE_MAPPING[discovery_method]
    except Exception:
        e = DiscoveryMethodNotSupported(discovery_method=discovery_method)
        logger.exception(e)
        raise e


def get_discovery_rules(discovery_rule_list: list[str], discovery_rule_ext: str):
    discovery_rules_to_run: set[Path] = set([])
    for discovery_rule in discovery_rule_list:
        try:
            discovery_rule_path = Path(discovery_rule).resolve()
        except Exception:
            logger.warning(errors.wrongDiscoveryRule(discovery_rule) + " It is not a valid path. The script will try to continue ignoring this discovery rule.")
        if discovery_rule_path.is_dir():
            for p in discovery_rule_path.glob('**/*' + discovery_rule_ext):
                discovery_rules_to_run.add(p)
        elif str(discovery_rule_path).endswith(discovery_rule_ext) and discovery_rule_path.is_file():
            discovery_rules_to_run.add(discovery_rule_path)
        else:
            logger.warning(errors.wrongDiscoveryRule(discovery_rule)+ " The script will try to continue ignoring this discovery rule.")
    return list(discovery_rules_to_run)


def build_timestamp_language_name(name: Path | None, language: str, now: datetime, extra: str = None) -> str:
    res = language
    if name:
        res = f"{res}_{name}"
    if extra:
        res = f"{extra}_{res}"
    if now:
        nowstr = now.strftime("%Y-%m-%d-%H-%M-%S")
        res = f"{nowstr}_{res}"
    return res


################################################################################
# Others
#

def check_tp_lib(tp_lib_path: Path):
    if not tp_lib_path.is_dir():
        e = TPLibDoesNotExist()
        logger.error(e.message)
        raise e


def check_lang_tp_lib_path(lang_tp_lib_path: Path):
    if not lang_tp_lib_path.is_dir():
        e = LanguageTPLibDoesNotExist()
        logger.error(e.message)
        raise e


def check_target_dir(target_dir: Path):
    if not target_dir.is_dir():
        e = TargetDirDoesNotExist()
        logger.error(e.message)
        raise e


def filter_sast_tools(itools: list[Dict], language: str, exception_raised=True):
    for t in itools:
        t["supported_languages"] = load_sast_specific_config(t["name"], t["version"])["supported_languages"]
    tools = list(filter(lambda x: language in x["supported_languages"], itools))
    if exception_raised and not tools:
        e = InvalidSastTools()
        logger.error(e.message)
        raise e
    return tools


def load_yaml(fpath):
    with open(fpath) as f:
        fdict: Dict = yaml.load(f, Loader=yaml.Loader)
    return fdict


def load_sast_specific_config(tool_name: str, tool_version: str) -> Dict:
    try:
        tool_config_path: Path = config.ROOT_SAST_DIR / load_yaml(config.SAST_CONFIG_FILE)["tools"][tool_name]["version"][tool_version]["config"]
    except KeyError:
        e = InvalidSastTool(f"{tool_name}:{tool_version}")
        raise e
    return load_yaml(tool_config_path)


def write_csv_file(ofile: Path, header: list[str], data: list[dict]):
    with open(ofile, "w") as report:
        writer = csv.DictWriter(report, fieldnames=header)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def add_logger(output_dir_path: Path, filename: str=None):
    if not filename:
        logfilename = config.logfile
    else:
        logfilename = filename
    if (output_dir_path and output_dir_path != config.RESULT_DIR) or (filename != config.logfile):
        loggermgr.add_logger(output_dir_path / logfilename)


def get_operation_build_name_and_dir(op: str, src_dir: Path | None, language: str, output_dir: Path):
    now = datetime.now()
    if not src_dir:
        build_name: str = build_timestamp_language_name(None, language, now)
    else:
        build_name: str = build_timestamp_language_name(src_dir.name, language, now)
    op_output_dir = output_dir / f"{op}_{build_name}"
    op_output_dir.mkdir(parents=True, exist_ok=True)
    return build_name, op_output_dir