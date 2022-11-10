import os
from datetime import datetime
from platform import system

from importlib import import_module
from pathlib import Path
from typing import Tuple

from core import pattern
from core.exceptions import PatternDoesNotExists, LanguageTPLibDoesNotExist
from core.instance import PatternCategory, FeatureVsInternalApi


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


# def get_all_nested_tuples_from_dict(d: Dict) -> Set:
#     stack = list(d.items())
#     visited = set()
#     res = set()
#     while stack:
#         k, v = stack.pop()
#         if isinstance(v, dict):
#             if k not in visited:
#                 stack.extend(v.items())
#         else:
#             if isinstance(v, list):
#                 for el in v:
#                     res.add((k, el))
#             else:
#                 res.add((k, v))
#         visited.add(k)
#
#     return res


def get_pattern_id_from_pattern_name(name: str) -> int:
    return get_instance_id_from_instance_name(name)


def get_instance_id_from_instance_name(name: str) -> int:
    return int(name.split("_")[0])


def get_class_from_str(class_str: str) -> object:
    try:
        module_path, class_name = class_str.rsplit('.', 1)
        module = import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(class_str)


def get_last_measurement_for_pattern_instance(meas_inst_dir: Path) -> Path:
    measurements: list[Path] = list(meas_inst_dir.iterdir())
    sorted_meas: list[Tuple[datetime, Path]] = list(sorted(
        zip(
            map(lambda m: datetime.strptime(m.name.split(".")[0].split("measurement-")[1], "%Y-%m-%d_%H-%M-%S"),
                measurements),
            measurements), key=lambda k: k[0]))
    return sorted_meas[-1][1]


def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file),
                       os.path.relpath(os.path.join(root, file),
                                       os.path.join(path, '..')))


def get_path_or_none(p: str) -> Path | None:
    if p is not None:
        return Path(p)
    return p


def get_pattern_category_or_none(el) -> PatternCategory | None:
    try:
        return PatternCategory(el)
    except ValueError:
        return None


def get_feature_vs_internal_api_or_none(el) -> FeatureVsInternalApi | None:
    try:
        return FeatureVsInternalApi(el)
    except ValueError:
        return None


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
