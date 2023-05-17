import json
import shutil
import uuid
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Dict, Tuple

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

import core.instance
from core import errors
from core import utils, analysis
from core.exceptions import PatternValueError
from core.instance import Instance, PatternCategory, FeatureVsInternalApi, instance_from_dict
from core.pattern import Pattern, get_pattern_by_pattern_id
from core.sast_job_runner import SASTjob, job_list_to_dict
from core.measurement import meas_list_to_tp_dict

def add_testability_pattern_to_lib(language: str, pattern_dict: Dict, pattern_src_dir: Path | None,
                                   pattern_lib_dest: Path) -> Path:
    try:
        pattern: Pattern = Pattern(pattern_dict["name"], language,
                                   [pattern_src_dir / instance_relative_path for instance_relative_path in
                                    pattern_dict["instances"] if
                                    pattern_src_dir], pattern_dict["family"], pattern_dict["description"],
                                   pattern_dict["tags"], pattern_dir=pattern_lib_dest)
    except KeyError as e:
        raise PatternValueError(message=errors.patternKeyError(e))

    pattern_instances_json_refs = pattern.instances
    pattern.instances = []
    pattern.add_pattern_to_tp_library(language, pattern_src_dir, pattern_lib_dest)

    if pattern_src_dir:
        for instance_json in pattern_instances_json_refs:
            add_tp_instance_to_lib_from_json(
                language, pattern.pattern_id, (pattern_src_dir / instance_json), pattern_src_dir, pattern_lib_dest
            )
    return pattern_lib_dest / language / utils.get_pattern_dir_name_from_name(pattern_src_dir.name, pattern.pattern_id)


def add_tp_instance_to_lib(language: str, pattern: Pattern, instance_dict: Dict, inst_old_name: str,
                           pattern_src_dir: Path, pattern_lib_dst: Path) -> Path:
    instance: Instance = Instance(
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "code", "path")),  # code_path: Path,
        utils.get_from_dict(instance_dict, "code", "injection_skeleton_broken"),  # code_injection_skeleton_broken: bool,
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "compile", "dependencies")),  # compile_dependencies: Path, # added 092022
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "compile", "binary")),  # compile_binary: Path,
        utils.get_from_dict(instance_dict, "compile", "instruction"),  # compile_instruction: str,  # added 092022
        utils.get_from_dict(instance_dict, "remediation", "transformation"),  # remediation_transformation: str, # added 092022
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "remediation", "modeling_rule")),  # remediation_modeling_rule: Path, # added 092022
        utils.get_from_dict(instance_dict, "remediation", "notes"),  # remediation_notes: str, # added 092022
        core.instance.get_pattern_category_or_none(utils.get_from_dict(instance_dict, "properties", "category")),
        utils.get_from_dict(instance_dict, "properties", "negative_test_case"),
        utils.get_from_dict(instance_dict, "properties", "source_and_sink"),
        utils.get_from_dict(instance_dict, "properties", "input_sanitizer"),
        core.instance.get_feature_vs_internal_api_or_none(utils.get_from_dict(instance_dict, "properties", "feature_vs_internal_api")),
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "discovery", "rule")),
        utils.get_from_dict(instance_dict, "discovery", "method"),
        utils.get_from_dict(instance_dict, "discovery", "rule_accuracy"),
        utils.get_from_dict(instance_dict, "discovery", "notes"),
        utils.get_from_dict(instance_dict, "expectation", "expectation"),
        utils.get_from_dict(instance_dict, "expectation", "type"),
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "expectation", "sink_file")),
        utils.get_from_dict(instance_dict, "expectation", "sink_line"),
        utils.get_path_or_none(utils.get_from_dict(instance_dict, "expectation", "source_file")),
        utils.get_from_dict(instance_dict, "expectation", "source_line"),
        pattern.name,
        pattern.description,
        pattern.family,
        pattern.tags,
        pattern.instances,
        language,
        pattern.pattern_id,
        pattern_dir=pattern_lib_dst
    )

    inst_name = utils.get_instance_dir_name_from_pattern(pattern_src_dir.name, pattern.pattern_id, instance.instance_id)
    pattern_name = utils.get_pattern_dir_name_from_name(pattern_src_dir.name, pattern.pattern_id)

    instance_src_dir: Path = pattern_src_dir / inst_old_name
    instance_dst_dir: Path = pattern_lib_dst / language / pattern_name / inst_name

    instance.add_instance_to_pattern_id(language, pattern_src_dir, pattern_lib_dst)
    pattern.add_new_instance_reference(language, pattern_lib_dst, f"./{inst_name}/{inst_name}.json")

    for path in list(instance_src_dir.iterdir()):
        if not path.suffix.endswith("json"):
            dst_path = instance_dst_dir / path.name
            if path.is_dir():
                shutil.copytree(path, dst_path)
            else:
                shutil.copy(path, dst_path)


def add_testability_pattern_to_lib_from_json(language: str, pattern_json: Path, pattern_src_dir: Path,
                                             pattern_lib_dest: Path) -> Path:
    with open(pattern_json) as json_file:
        try:
            pattern: Dict = json.load(json_file)
        except JSONDecodeError as e:
            raise e
    try:
        return add_testability_pattern_to_lib(language, pattern, pattern_src_dir, pattern_lib_dest)
    except PatternValueError as e:
        raise e


def add_tp_instance_to_lib_from_json(language: str, pattern_id: int, instance_json: Path,
                                     pattern_src_dir: Path, pattern_dest_dir: Path):
    pattern, p_dir = get_pattern_by_pattern_id(language, pattern_id, pattern_dest_dir)

    with open(instance_json) as json_file:
        try:
            instance: Dict = json.load(json_file)
        except JSONDecodeError as e:
            raise e
    return add_tp_instance_to_lib(
        language, pattern, instance, instance_json.parent.name, pattern_src_dir, pattern_dest_dir
    )


async def start_add_measurement_for_pattern(language: str, sast_tools: list[Dict], tp_id: int, now,
                                            tp_lib_dir: Path, output_dir: Path) -> Dict:
    d_status_tp = {}
    try:
        l_tpi_path: list[Path] = utils.list_tpi_paths_by_tp_id(language, tp_id, tp_lib_dir)
        target_pattern, p_dir = get_pattern_by_pattern_id(language, tp_id, tp_lib_dir)
    except Exception as e:
        logger.warning(
            f"SAST measurement - failed in fetching instances for pattern {tp_id}. Pattern will be ignored. Exception raised: {utils.get_exception_message(e)}")
        return d_status_tp

    for path in l_tpi_path:
        try:
            tpi_id = utils.get_id_from_name(path.name)
            with open(path) as instance_json_file:
                instance_json: Dict = json.load(instance_json_file)
            target_instance: Instance = instance_from_dict(instance_json, target_pattern, language, tpi_id)
            d_status_tp[tpi_id]: list[SASTjob] = await analysis.analyze_pattern_instance(
                target_instance, path.parent, sast_tools, language, now, output_dir
            )
        except Exception as e:
            d_status_tp[tpi_id] = []
            logger.warning(
                f"SAST measurement - failed in preparing SAST jobs for instance at {path} of the pattern {tp_id}. Instance will be ignored. Exception raised: {utils.get_exception_message(e)}")
            continue
    return d_status_tp


async def save_measurement_for_patterns(language: str, now: datetime,
                                        l_job: list[SASTjob],
                                        tp_lib_dir: Path):

    d_job = job_list_to_dict(l_job)
    l_meas = await analysis.inspect_analysis_results(d_job, language)
    d_tp_meas = meas_list_to_tp_dict(l_meas)

    for tp_id in d_tp_meas:
        for tpi_id in d_tp_meas[tp_id]:
            l_tpi_meas = []
            for meas in d_tp_meas[tp_id][tpi_id]:
                # meas.instance
                tp_rel_dir = utils.get_pattern_dir_name_from_name(meas.instance.name, meas.instance.pattern_id)
                tpi_rel_dir = utils.get_instance_dir_name_from_pattern(meas.instance.name, meas.instance.pattern_id, meas.instance.instance_id)
                meas_dir = utils.get_measurement_dir_for_language(tp_lib_dir, language) / tp_rel_dir / tpi_rel_dir
                meas_dir.mkdir(parents=True, exist_ok=True)
                d_tpi_meas_ext: Dict = meas.__dict__
                # TODO: rather than extending here we should extend the Measurement class
                d_tpi_meas_ext["pattern_id"] = meas.instance.pattern_id
                d_tpi_meas_ext["instance_id"] = meas.instance.instance_id
                d_tpi_meas_ext["language"] = language
                d_tpi_meas_ext["instance"] = f"./{meas.instance.language}/{tp_rel_dir}/{tpi_rel_dir}/{tpi_rel_dir}.json"
                l_tpi_meas.append(d_tpi_meas_ext)

            with open(meas_dir / utils.get_measurement_file(now), "w") as f_meas:
                json.dump(l_tpi_meas, f_meas, indent=4)