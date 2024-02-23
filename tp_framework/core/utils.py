import csv
import hashlib
import json
import shutil
import os
import yaml

from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Tuple, Dict


import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

import config
from core.exceptions import PatternDoesNotExists, LanguageTPLibDoesNotExist, TPLibDoesNotExist, \
    DiscoveryMethodNotSupported, TargetDirDoesNotExist, InstanceDoesNotExists, \
    MeasurementResultsDoNotExist

from core import errors


################################################################################
# PATTERNS
#


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


################################################################################
# INSTANCES
#


# TODO: TESTING
def get_instance_dir_from_list(instance_id: int, l_pattern_dir: list[Path]):
    instance_with_id = list(filter(lambda tpi_dir: get_id_from_name(tpi_dir.name) == instance_id, l_pattern_dir))
    if not instance_with_id:
        raise InstanceDoesNotExists(instance_id=instance_id)
    return instance_with_id[0]



################################################################################
# MEASUREMENT
#


def get_measurement_dir_for_language(tp_lib_dir: Path, language: str):
    return Path(tp_lib_dir / config.MEASUREMENT_REL_DIR / language)


# TODO: TESTING
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


def check_measurement_results_exist(measurement_dir: Path):
    if not measurement_dir.is_dir():
        e = MeasurementResultsDoNotExist()
        logger.error(get_exception_message(e))
        raise e


################################################################################
# DISCOVERY
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
# SAST
#

def sast_tool_version_match(v1, v2, nv_max=3, ignore_saas=True):
    if ignore_saas and (v1 == "saas" or v2 == "saas"):
        return True
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


################################################################################
# PATTERN REPAIR
#


def check_file_exist(file_path: Path, file_suffix = ".csv"):
    if not file_path.is_file() or not file_path.suffix == file_suffix:
        e = FileNotFoundError(file_path)
        logger.error(get_exception_message(e))
        raise e


def get_relative_paths(file_path: Path, base_path: Path):
    if not file_path:
        return None
    try:
        return f"./{file_path.relative_to(base_path)}"
    except ValueError:
        try:
            return f"../{file_path.relative_to(base_path.parent)}"
        except ValueError as e:
            logger.warning(f"Could not parse filepath {file_path} to a relative path.")
            return file_path


def read_csv_to_dict(path_to_file: str) -> dict:
    # Reads a csv file into a dictionary, the csv file must contain the columns 'pattern_id', 'instance_id', 'language', 'successful'
    # The dict will have the form: {<language>: {<pattern_id>: {<instance_id>: <successful>}}}
    res = []
    with open(path_to_file, "r") as csvfile:
        r = csv.reader(csvfile, delimiter=",")
        headings = next(r)
        wanted_columns = ["pattern_id", "instance_id", "language", "successful"]
        wanted_idx = [headings.index(w) for w in wanted_columns]
        assert len(wanted_idx) == len(wanted_columns), f"Could not find wanted column names in csv {path_to_file}"
        sanitized_lines =filter(lambda x: bool(x[0].strip()), r)
        res = [[line[i].strip() for i in wanted_idx] for line in sanitized_lines]
    
    ret = {}
    for line in res:
        if line[2] not in ret.keys():
            ret[line[2]] = {}
        if line[0] not in ret[line[2]].keys():
            ret[line[2]][line[0]] = {}
        if line[1] not in ret[line[2]][line[0]].keys():
            ret[line[2]][line[0]][line[1]] = {}
        ret[line[2]][line[0]][line[1]] = line[3]
    return ret


def translate_bool(bool_to_translate: bool):
    return "yes" if bool_to_translate else "no"

# TODO TESTING
def get_language_by_file_ending(filename: str) -> str:
    if not filename:
        return ""
    if Path(filename).suffix == ".py":
        return "python"
    if Path(filename).suffix == ".php":
        return "php"
    if Path(filename).suffix == ".js":
        return "javascript"
    if Path(filename).suffix == ".java":
        return "java"
    if Path(filename).suffix == ".sc":
        return "scala"
    if Path(filename).suffix == ".bash":
        return "bash"
    return ""

################################################################################
# OTHER
# TODO: Could be sorted alphabetically?


# Useful for some SAST tools that accepts a zip file of the source code to scan
def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file),
                       os.path.relpath(os.path.join(root, file),
                                       os.path.join(path, '..')))


def get_id_from_name(name: str) -> int:
    return int(name.split("_")[0])


# TODO (LC): are these related to pattern instance ?
def get_path_or_none(p: str) -> Path | None:
    if p:
        return Path(p)
    return None


def get_from_dict(d: dict, k1: str, k2: str):
    try:
        return d.get(k1, {}).get(k2, None)
    except AttributeError:
        return None


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


def load_yaml(fpath):
    with open(fpath) as f:
        fdict: Dict = yaml.load(f, Loader=yaml.Loader)
    return fdict


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


def list_files(path_to_parent_dir: Path, suffix: str, recursive: bool = False):
    assert suffix[0] == ".", "Suffix has to start with '.'"
    if recursive:
        matches = []
        for root, _, filenames in os.walk(path_to_parent_dir):
            for filename in filter(lambda f: Path(f).suffix == suffix, filenames):
                matches += [Path(root)  / filename]
        return matches
    else:
        return list(filter(lambda file_name: file_name.suffix == suffix, [path_to_parent_dir / f for f in path_to_parent_dir.iterdir()]))


def list_directories(parent_dir: Path):
    return list(filter(lambda name: name.is_dir(), [parent_dir / d for d in parent_dir.iterdir()]))

# TODO: TESTING
def get_json_file(path_to_pattern_or_instance: Path) -> Path:
    if path_to_pattern_or_instance.name == 'docs':
        return None
    json_files_in_dir = list_files(path_to_pattern_or_instance, ".json")
    if len(json_files_in_dir) == 1:
        return json_files_in_dir[0]
    elif not json_files_in_dir:
        logger.warning(f"Could not find a JSON file in {path_to_pattern_or_instance.name}")
        return None
    else:
        logger.warning(f"Found multiple '.json' files for {path_to_pattern_or_instance.name}")
        if path_to_pattern_or_instance / f"{path_to_pattern_or_instance.name}.json" in json_files_in_dir:
            return path_to_pattern_or_instance / f"{path_to_pattern_or_instance.name}.json"
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


def write_json(path_to_json_file: Path, result_dict: dict):
    path_to_json_file.parent.mkdir(exist_ok=True, parents=True)
    with open(path_to_json_file, "w") as json_file:
        json.dump(result_dict, json_file, indent=4)


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
