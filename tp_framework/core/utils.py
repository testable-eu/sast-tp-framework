import csv
import os
import json
from datetime import datetime
from platform import system
import shutil

from importlib import import_module
from pathlib import Path
from typing import Tuple, Dict
import yaml

import hashlib

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

import config
from core import pattern, instance
from core.exceptions import PatternDoesNotExists, LanguageTPLibDoesNotExist, TPLibDoesNotExist, InvalidSastTools, \
    DiscoveryMethodNotSupported, TargetDirDoesNotExist, InvalidSastTool, PatternFolderNotFound, InstanceDoesNotExists, \
    FileDoesNotExist, TemplateDoesNotExist, MeasurementResultsDoNotExist

from core import errors


def is_windows():
    return system() == "Windows"


def list_pattern_paths_for_language(language: str, tp_lib_dir: Path) -> list[Path]:
    all_pattern_dirs_by_lang: Path = tp_lib_dir / language
    if not all_pattern_dirs_by_lang.is_dir():
        raise LanguageTPLibDoesNotExist
    return list_dirs_only(all_pattern_dirs_by_lang)


def list_tpi_paths_by_tp_id(language: str, pattern_id: int, tp_lib_dir: Path) -> list[Path]:
    try:
        p, p_dir = pattern.get_pattern_by_pattern_id(language, pattern_id, tp_lib_dir)
        return list(map(lambda i: (tp_lib_dir / language / p_dir / i).resolve(), p.instances))
    except:
        ee = PatternDoesNotExists(pattern_id)
        logger.exception(ee)
        raise ee


def get_tpi_id_from_jsonpath(jp: Path) -> int:
    return get_id_from_name(jp.parent.name)


def get_pattern_dir_from_id(pattern_id: int, language: str, tp_lib_dir: Path) -> Path: # needed
    tp_lib_dir_lang_dir: Path = tp_lib_dir / language
    if tp_lib_dir_lang_dir.is_dir():
        pattern_with_id = list(filter(lambda p: get_id_from_name(p.name) == pattern_id, list_dirs_only(tp_lib_dir_lang_dir)))
        if pattern_with_id:
            return Path(pattern_with_id[0])
        raise PatternDoesNotExists(pattern_id)
    else:
        raise PatternDoesNotExists(pattern_id)


def get_next_free_pattern_id_for_language(language: str, tp_lib_dir: Path, proposed_id = None):
    lang_tp_lib_path = tp_lib_dir / language
    check_lang_tp_lib_path(lang_tp_lib_path)
    all_patterns = list_dirs_only(lang_tp_lib_path)
    taken_ids = []
    for pattern in all_patterns:
        taken_ids += [get_id_from_name(pattern.name)]
    id_range = list(range(1, max(taken_ids)+1))
    free_ids = sorted(list(set(id_range) - set(taken_ids)))
    if proposed_id in free_ids:
        return proposed_id
    return free_ids[0] if free_ids else max(taken_ids) + 1


def get_instance_dir_from_id(instance_id: int, pattern_dir: Path) -> Path:
    if pattern_dir.is_dir():
        return get_instance_dir_from_list(instance_id, list_dirs_only(pattern_dir))
    else:
        raise PatternFolderNotFound()


def get_instance_dir_from_list(instance_id: int, l_pattern_dir: list[Path]):
    instance_with_id = list(filter(lambda tpi_dir: get_id_from_name(tpi_dir.name) == instance_id, l_pattern_dir))
    if not instance_with_id:
        raise InstanceDoesNotExists()
    return instance_with_id[0]

# def get_or_create_language_dir(language: str, tp_lib_dir: Path) -> Path:
#     tp_lib_for_lang: Path = tp_lib_dir / language
#     tp_lib_for_lang.mkdir(parents=True, exist_ok=True)
#     return tp_lib_for_lang


def get_or_create_pattern_dir(language: str, pattern_id: int, pattern_name: str, tp_lib_dir: Path) -> Path:
    pattern_dir = tp_lib_dir / language / get_pattern_dir_name_from_name(pattern_name, pattern_id)
    pattern_dir.mkdir(parents=True, exist_ok=True)
    return pattern_dir


def get_pattern_dir_name_from_name(name: str, pattern_id: int) -> str:
    return f"{pattern_id}_{name.lower().replace(' ', '_')}"


def get_instance_dir_name_from_pattern(name: str, pattern_id: int, instance_id: int) -> str:
    return f"{instance_id}_instance_{get_pattern_dir_name_from_name(name, pattern_id)}"


def get_id_from_name(name: str) -> int:
    return int(name.split("_")[0])


def get_class_from_str(class_str: str) -> object:
    try:
        module_path, class_name = class_str.rsplit('.', 1)
        module = import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(class_str)


def get_tp_dir_for_language(tp_lib_dir: Path, language: str):
    return Path(tp_lib_dir / language)


def get_measurement_dir_for_language(tp_lib_dir: Path, language: str):
    return Path(tp_lib_dir / config.MEASUREMENT_REL_DIR / language)


def get_measurement_file(date: datetime):
    date_time_str = date.strftime("%Y-%m-%d_%H-%M-%S")
    return f"measurement-{date_time_str}.json"


def get_last_measurement_for_pattern_instance(meas_inst_dir: Path) -> Path:
    measurements: list[Path] = list(meas_inst_dir.iterdir())
    if len(measurements) == 1:
        return measurements[0]
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
# TODO (LC): are these related to pattern instance ?
#
def get_path_or_none(p: str) -> Path | None:
    if p:
        return Path(p)
    return p


def get_enum_value_or_none(enum) -> str | None:
    try:
        return enum.value
    except AttributeError:
        return None


def get_relative_path_str_or_none(path) -> str | None:
    if path:
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
                # related to #42
                if p.name.startswith(config.PATCHED_PREFIX):
                    continue
                discovery_rules_to_run.add(p)
        elif str(discovery_rule_path).endswith(discovery_rule_ext) and discovery_rule_path.is_file():
            discovery_rules_to_run.add(discovery_rule_path)
        else:
            logger.warning(errors.wrongDiscoveryRule(discovery_rule)+ " The script will try to continue ignoring this discovery rule.")
    return list(discovery_rules_to_run)


################################################################################
# Others
#

def check_measurement_results_exist(measurement_dir: Path):
    if not measurement_dir.is_dir():
        e = MeasurementResultsDoNotExist()
        logger.error(get_exception_message(e))
        raise e


def check_file_exist(file_path: Path, file_suffix = ".csv"):
    if not file_path.is_file() or not file_path.suffix == file_suffix:
        e = FileDoesNotExist(file_path)
        logger.error(get_exception_message(e))
        raise e


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


def check_tp_lib(tp_lib_path: Path):
    if not tp_lib_path.is_dir():
        e = TPLibDoesNotExist()
        logger.error(get_exception_message(e))
        raise e


def check_lang_tp_lib_path(lang_tp_lib_path: Path):
    if not lang_tp_lib_path.is_dir():
        e = LanguageTPLibDoesNotExist()
        logger.error(get_exception_message(e))
        raise e


def check_target_dir(target_dir: Path):
    if not target_dir.is_dir():
        e = TargetDirDoesNotExist()
        logger.error(get_exception_message(e))
        raise e


def filter_sast_tools(itools: list[Dict], language: str, exception_raised=True):
    for t in itools:
        t["supported_languages"] = load_sast_specific_config(t["name"], t["version"])["supported_languages"]
    tools = list(filter(lambda x: language in x["supported_languages"], itools))
    if exception_raised and not tools:
        e = InvalidSastTools()
        logger.error(get_exception_message(e))
        raise e
    return tools


def sast_tool_version_match(v1, v2, nv_max=3):
    sv1 = v1.split(".")
    sv2 = v2.split(".")
    nv = max(len(sv1), len(sv2))
    for i in range(0, min(nv, nv_max)):
        try:
            if sv1[i] != sv2[i]:
                return False
        except IndexError:
            return False
    return True


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
    with open(ofile, "w", newline='') as report:
        writer = csv.DictWriter(report, fieldnames=header)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def add_loggers(output_dir_path: Path, filename: str=None, console=True):
    if not filename:
        logfilename = config.logfile
    else:
        logfilename = filename
    if (output_dir_path and output_dir_path != config.RESULT_DIR) or (logfilename != config.logfile):
        loggermgr.add_logger(output_dir_path / logfilename)
    if console:
        loggermgr.add_console_logger()



def get_operation_build_name_and_dir(op: str, src_dir: Path | None, language: str, output_dir: Path):
    now = datetime.now()
    if not src_dir:
        build_name: str = build_timestamp_language_name(None, language, now)
    else:
        build_name: str = build_timestamp_language_name(src_dir.name, language, now)
    op_output_dir = output_dir / f"{op}_{build_name}"
    op_output_dir.mkdir(parents=True, exist_ok=True)
    return build_name, op_output_dir


def report_results(results, output_dir, header, export_file=None):
    if export_file:
        write_csv_file(output_dir / export_file, header, results)
    else:
        print(",".join(header))
        for row in results:
            print(",".join([str(row[h]) for h in header]))


def get_exception_message(e):
    if hasattr(e, 'message'):
        return e.message
    elif hasattr(e, 'msg'):
        return e.msg
    else:
        return str(e)


def get_tp_op_status_string(t_tp_info, status="started...", op=None):
    return get_tpi_op_status_string(t_tp_info, t_tpi_info=None, status=status, op=op)


def get_tpi_op_status_string(t_tp_info, t_tpi_info=None, status="started...", op=None):
    i, tot, tp_id = t_tp_info
    tpi_id_str = ""
    tpi_count_str = ""
    if t_tpi_info:
        j, tpi_tot, tpi_id = t_tpi_info
        tpi_count_str = f" {j}/{tpi_tot} -"
        tpi_id_str = f", instance id {tpi_id}"
    op_str = ""
    if op:
        op_str = f"{op} - "
    return f"{i}/{tot} -{tpi_count_str} {op_str}pattern id {tp_id}{tpi_id_str}: {status}"


def list_dirs_only(dir: Path):
    return [e for e in dir.iterdir() if e.is_dir()]


def get_file_hash(fpath, bigfile=False):
    with open(fpath, "rb") as f:
        hash = hashlib.md5()
        if not bigfile:
            hash.update(f.read())
        else:
            while chunk := f.read(8192):
                hash.update(chunk)
    return hash.hexdigest()



########################### New utils

def list_files(path_to_parent_dir: Path, suffix: str):
    assert suffix[0] == ".", "Suffix has to start with '.'"
    return list(filter(lambda file_name: file_name.suffix == suffix, [path_to_parent_dir / f for f in os.listdir(path_to_parent_dir)]))


def get_pattern_json(path_to_pattern: Path) -> Path:
    json_files_in_pattern_dir = list_files(path_to_pattern, ".json")
    if len(json_files_in_pattern_dir) == 1:
        return json_files_in_pattern_dir[0]
    elif not json_files_in_pattern_dir:
        logger.warning(f"Could not find a pattern JSON file in {path_to_pattern.name}")
        return None
    else:
        logger.warning(f"Found multiple '.json' files for {path_to_pattern.name}")
        if path_to_pattern / f"{path_to_pattern.name}.json" in json_files_in_pattern_dir:
            return path_to_pattern / f"{path_to_pattern.name}.json"
        logger.warning("Could not determine the right pattern JSON file. Please name it <pattern_id>_<pattern_name>.json")
        return None


def read_json(path_to_json_file: Path):
    if not path_to_json_file.is_file():
        return {}
    result = {}
    
    try:
        with open(path_to_json_file, "r") as json_file:
            result = json.load(json_file)
    except json.JSONDecodeError as err:
        raise Exception(f"JSON is corrupt, please check {path_to_json_file}") from err
    
    if not result:
        logger.error(f"JSON file is empty")
    return result


def copy_dir_content(path_to_src_dir: Path, path_to_dst_dir: Path):
    for element in os.listdir(path_to_src_dir):
        src_path = path_to_src_dir / element
        dest_path = path_to_dst_dir / element
        if dest_path.exists():
            continue
        if src_path.is_file():
            shutil.copy2(src_path, dest_path)
        else:
            shutil.copytree(src_path, dest_path)


if __name__ == "__main__":
    print(get_pattern_json(Path('./testability_patterns/PHP/85_test_pattern')))