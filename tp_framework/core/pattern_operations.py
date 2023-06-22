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

# import core.instance
from core import errors
from core import utils, analysis
from core.exceptions import PatternValueError
from core.instance import Instance #, PatternCategory, FeatureVsInternalApi # , instance_from_dict
from core.pattern import Pattern, list_tpi_paths_by_tp_id, get_pattern_by_pattern_id
from core.sast_job_runner import SASTjob, job_list_to_dict
from core.measurement import meas_list_to_tp_dict


def add_testability_pattern_to_lib_from_json(language: str, pattern_json: Path, pattern_src_dir: Path,
                                             pattern_lib_dest: Path) -> Path:
    # The pattern objects automatically initializes the instances as well
    pattern = Pattern.init_from_json_file_without_pattern_id(pattern_json, language, pattern_src_dir, pattern_lib_dest)
    # dump the pattern to the tplib
    pattern.copy_to_tplib()
    logger.info(f"The pattern has been copied to {pattern.pattern_path}, You might need to adjust relative path links.")
    return pattern


async def start_add_measurement_for_pattern(language: str, sast_tools: list[Dict], tp_id: int, now,
                                            tp_lib_dir: Path, output_dir: Path) -> Dict:
    d_status_tp = {}
    try:
        target_pattern = Pattern.init_from_id_and_language(tp_id, language, tp_lib_dir)
    except Exception as e:
        logger.warning(
            f"SAST measurement - failed in fetching instances for pattern {tp_id}. Pattern will be ignored. Exception raised: {utils.get_exception_message(e)}")
        return d_status_tp

    for instance in target_pattern.instances:
        try:
            d_status_tp[target_pattern.pattern_id]: list[SASTjob] = await analysis.analyze_pattern_instance(
                instance, sast_tools, language, now, output_dir
            )
        except Exception as e:
            d_status_tp[target_pattern.pattern_id] = []
            logger.warning(
                f"SAST measurement - failed in preparing SAST jobs for instance at {instance.instance_path} of the pattern {tp_id}. Instance will be ignored. Exception raised: {utils.get_exception_message(e)}")
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