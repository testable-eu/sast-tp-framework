import csv
import json
import logging

from collections import defaultdict
from os import path, listdir, walk
from pathlib import Path

from core.errors import templateDirDoesNotExist
from core.exceptions import TemplateDoesNotExist, PatternDoesNotExists, FileDoesNotExist
from core.utils import get_exception_message
from core import loggermgr

logger = logging.getLogger(loggermgr.logger_name(__name__))

INSTANCE_JSON_NOT_MANDATORY_KEYS = ["description", "reporting"]


def assert_pattern_valid(path_to_pattern: Path) -> None:
    """Asserts that a pattern is a valid directory

    Args:
        path_to_pattern (Path): absolute path to a pattern

    Raises:
        e: PatternDoesNotExists error, when pattern does not exist.
    """
    if not Path(path_to_pattern).is_dir():
        e = PatternDoesNotExists()
        logger.error(get_exception_message(e))
        raise e


def compare_dicts(old_dict, new_dict) -> dict:
    return {
        k: old_dict[k] for k in old_dict if k in new_dict and old_dict[k] != new_dict[k]
    }


def get_dict_keys(d: dict) -> list:
    """Returns a list of keys in a multidimensional dict.
    The keynames are seperated by `:` i.e. `level1_key:level2_key`

    Args:
        d (dict): a multidimensional dict

    Returns:
        list: all keys from all dict level
    """
    all_keys = []
    current_keys = d.keys()
    for k in current_keys:
        if isinstance(d[k], dict):
            sub_keys = get_dict_keys(d[k])
            all_keys += [f"{k}:{sk}" for sk in sub_keys]
        else:
            all_keys += [k]
    return all_keys


def get_instance_name(path_to_instance) -> str:
    return " ".join(path.basename(path_to_instance).split("_")[:2]).title()


def get_files_with_ending(
        path_to_dir: str, file_ending: str, recursive: bool = False
    ) -> list:
    """Returns all files with a certain ending. Be sure to include the `.` when passing the `file_ending` argument, i.e. `file_ending='.txt'`.

    Args:
        path_to_dir (str): Directories from which the files should be listed.
        file_ending (str): The ending of the files, that should be filtered for.
        recursive (bool, optional): Should the algorithm go through the directory recursivly?. Defaults to False.

    Returns:
        list: all filepaths, to files in the directory, having the `file_ending`.
    """
    matches = []
    for root, _, filenames in walk(path_to_dir):
        for filename in filter(lambda f: f.endswith(file_ending), filenames):
            matches.append(path.join(root, filename))
    return (
        matches
        if recursive
        else sorted(
            [
                path.join(path_to_dir, f)
                for f in filter(
                    lambda filename: Path(filename).suffix == file_ending,
                    listdir(path_to_dir),
                )
            ]
        )
    )


def get_template_dir_path(tp_lib_path) -> str:
    template_path = path.join(tp_lib_path, "pattern_template", "ID_pattern_name")
    if not path.isdir(template_path):
        e = TemplateDoesNotExist(templateDirDoesNotExist(template_path))
        logger.error(get_exception_message(e))
        raise e
    return template_path


def get_template_pattern_json_path(tp_lib_path) -> str:
    template__pattern_json_path = path.join(
        get_template_dir_path(tp_lib_path), "ID_pattern_name.json"
    )
    print(template__pattern_json_path)
    if not path.isfile(template__pattern_json_path):
        e = TemplateDoesNotExist(templateDirDoesNotExist(template__pattern_json_path))
        logger.error(get_exception_message(e))
        raise e
    return template__pattern_json_path


def get_template_instance_path(tp_lib_path) -> str:
    template_instance_path = path.join(
        get_template_dir_path(tp_lib_path), "IID_instance_ID_pattern_name"
    )
    if not path.isdir(template_instance_path):
        e = TemplateDoesNotExist(templateDirDoesNotExist(template_instance_path))
        logger.error(get_exception_message(e))
        raise e
    return template_instance_path


def get_template_instance_json_path(tp_lib_path) -> str:
    template_instance_json_path = path.join(
        get_template_instance_path(tp_lib_path), "IID_instance_ID_pattern_name.json"
    )
    if not path.isfile(template_instance_json_path):
        e = TemplateDoesNotExist(templateDirDoesNotExist(template_instance_json_path))
        logger.error(get_exception_message(e))
        raise e
    return template_instance_json_path


def get_template_instance_discovery_rule_path(tp_lib_path) -> str:
    template_instance_discovery_rule_path = path.join(
        get_template_instance_path(tp_lib_path), "pattern_discovery_rule.sc"
    )
    if not path.isfile(template_instance_discovery_rule_path):
        e = TemplateDoesNotExist(
            templateDirDoesNotExist(template_instance_discovery_rule_path)
        )
        logger.error(get_exception_message(e))
        raise e
    return template_instance_discovery_rule_path


def get_language_by_file_ending(filename: str) -> str:
    """Returns the language, by simply looking at the suffix of the file

    Args:
        filename (str): name of a file

    Raises:
        NotImplementedError: if the suffix is not yet supported, the function raises a NotImplementedError.

    Returns:
        str: language
    """
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
    raise NotImplementedError(
        f"The ending of the given filename {filename} is not yet supported"
    )


def list_directories(path_to_parent_directory: str):
    return [
        path.join(path_to_parent_directory, f)
        for f in listdir(path_to_parent_directory)
    ]


def list_instances_jsons(path_to_pattern: str | Path):
    return [
        path.join(instance, f"{path.basename(instance)}.json")
        for instance in filter(
            lambda x: path.isdir(x) and path.basename(x)[0].isdigit(),
            list_directories(path_to_pattern),
        )
    ]


def read_json(path_to_json: str) -> dict:
    result = {}
    try:
        with open(path_to_json, "r") as json_file:
            result = json.load(json_file)
    except json.JSONDecodeError as err:
        raise Exception(f"JSON is corrupt, please check {path_to_json}") from err
    if not result:
        logger.error(f"JSON file is empty")
    return result


def read_file(path_to_file: str) -> str:
    try:
        with open(path_to_file, "r") as file:
            ret = file.read()
    except Exception:
        e = FileDoesNotExist(
            f"The file {path_to_file} you wanted to read does not exist or is corrupt. Cannot read the file."
        )
        logger.error(get_exception_message(e))
        raise e
    return ret


def read_csv_to_dict(path_to_file: str) -> dict:
    """Reads a csv file into a dictionary, the csv file must contain the columns 'pattern_id', 'instance_id', 'language', 'successful'
    The dict will have the form:
    {<language>: {<pattern_id>: {<instance_id>: <successful>}}}

    Args:
        path_to_file (str): path to csv file (with discovery rule results)

    Returns:
        dict: defaultdict of dicts
    """
    res = []
    with open(path_to_file, "r") as csvfile:
        r = csv.reader(csvfile, delimiter=",")
        headings = next(r)
        wanted_columns = ["pattern_id", "instance_id", "language", "successful"]
        wanted_idx = [headings.index(w) for w in wanted_columns]
        assert len(wanted_idx) == len(
            wanted_columns
        ), f"Could not find wanted column names in csv {path_to_file}"
        res = [[line[i] for i in wanted_idx] for line in r]
    ret = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for line in res:
        ret[line[2]][line[0]][line[1]] = line[3]
    return ret


def repair_dict_keys(
    tested_dict: dict, ground_truth_dict: dict, not_mandatory_keys: list = []
) -> None:
    """Modifies `tested_dict` and inserts all keys from `ground_truth_dict`, that are not in `tested_dict`, except they are in `not_mandatory_keys`.

    Args:
        tested_dict (dict): Dict that has potentially missing keys.
        ground_truth_dict (dict): Dict that has all necessary keys
        not_mandatory_keys (list, optional): list of keys in `ground_truth_dict` that are not mandatory. Defaults to [].
    """
    tested_keys = set(tested_dict.keys())
    ground_truth_keys = set(ground_truth_dict.keys())

    common_keys = set.intersection(tested_keys, ground_truth_keys)
    for k in common_keys:
        if isinstance(tested_dict[k], dict) and isinstance(ground_truth_dict[k], dict):
            repair_dict_keys(tested_dict[k], ground_truth_dict[k], not_mandatory_keys)
        if isinstance(tested_dict[k], dict) != isinstance(ground_truth_dict[k], dict):
            logger.warning(
                f'One of the values for "{k}" is a dict, the other one is not'
            )

    missing_keys = ground_truth_keys - tested_keys
    unexpected_keys = tested_keys - ground_truth_keys
    for key in missing_keys:
        if key in not_mandatory_keys:
            continue
        tested_dict[key] = ""
        logger.info(f'Added "{key}"')
    if unexpected_keys:
        logger.warning(f'Keys "{list(unexpected_keys)}" is unexpected')


def repair_keys_of_json(
    path_to_json_tested: str,
    path_to_json_ground_truth: str,
    not_mandatory_keys: list = [],
) -> None:
    # checks if all keys from path_to_json_ground_truth are in path_to_json_tested, if not it adds them
    tested_json_dict = read_json(path_to_json_tested)
    template_json_dicts = read_json(path_to_json_ground_truth)
    repair_dict_keys(tested_json_dict, template_json_dicts, not_mandatory_keys)
    write_json(path_to_json_tested, tested_json_dict)


def translate_bool(to_translate: bool) -> str:
    return "yes" if to_translate else "no"


def write_json(path_to_json: str, result_dict: dict) -> None:
    with open(path_to_json, "w") as json_file:
        json.dump(result_dict, json_file, indent=4)
