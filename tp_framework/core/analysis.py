import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

from core import utils
from core.instance import Instance
from core.measurement import Measurement
from core.sast import SAST
from core.sast_job_runner import InQueue, OutQueue, SASTjob


async def analyze_pattern_instance(instance: Instance,
                                   tools: list[Dict], language: str,
                                   date: datetime, output_dir: Path) -> list[SASTjob]:
    logger.debug(f"SAST measurement - prepare SAST jobs for pattern {instance.pattern_id} instance {instance.instance_id} with {len(tools)} tools: started...")
    l_status_tpi: list[SASTjob] = []

    # pattern instance dependencies (if any)
    if instance.compile_dependencies:
        lib_dir: Path = instance.compile_dependencies
        logger.debug(f"Dependencies will be considered {lib_dir}")
    else:
        lib_dir = None
        logger.debug(f"No dependencies will be considered")

    for tool in tools:
        try:
            tool_name: str = tool["name"]
            tool_version: str = tool["version"]

            sast_config: Dict = core.utils.load_sast_specific_config(tool_name, tool_version)
            sast_interface_class: str = sast_config["tool_interface"]
            sast_class = utils.get_class_from_str(sast_interface_class)

            # noinspection PyCallingNonCallable
            sast: SAST = sast_class()
            sast_job: SASTjob = SASTjob(tool, tp_id=instance.pattern_id, tpi_id=instance.instance_id)
            job_id = sast_job.job_id

            # TODO: what about using the sast_job object in the queue?
            InQueue().put_nowait((job_id, tool_name, tool_version, instance, date,
                                  sast.launcher(instance.path, language, output_dir, lib_dir=lib_dir, measurement=True)))
            l_status_tpi.append(sast_job)
        except Exception as e:
            logger.warning(f"SAST measurement - failed for pattern {instance.pattern_id} instance {instance.instance_id} with tool {tool}. Instance will be ignored. Exception raised: {utils.get_exception_message(e)}")
            sast_job: SASTjob = SASTjob(tool, error=True)
            l_status_tpi.append(sast_job)
            continue
    logger.info(f"SAST measurement - prepared SAST jobs for pattern {instance.pattern_id} instance {instance.instance_id}")
    return l_status_tpi


async def inspect_analysis_results(d_job: Dict, language) -> list[Measurement]:
    measurements: list[Measurement] = []
    if not d_job:
        return measurements
    while True:
        while True:
            job_id_res, tool_name, tool_version, instance, date, csv_res = await OutQueue().get()
            if job_id_res in d_job and not d_job[job_id_res].is_extracted():
                d_job[job_id_res].set_extracted()
                OutQueue().task_done()
                break
            else:
                OutQueue().task_done()
                OutQueue().put_nowait((job_id_res, tool_name, tool_version, instance, date, csv_res))

        # if not csv_res, then the SAST job would have failed and no measurement in that case
        if csv_res:
            sast_config: Dict = core.utils.load_sast_specific_config(tool_name, tool_version)
            sast_interface_class: str = sast_config["tool_interface"]
            sast_class = utils.get_class_from_str(sast_interface_class)

            # noinspection PyCallingNonCallable
            sast: SAST = sast_class()

            if tool_version == "saas":
                tool_version = await sast.get_tool_version()

            findings: list[Dict] = sast.inspector(csv_res, language)
            measurement: Measurement = Measurement().define_verdict(date, instance, findings, tool_name, tool_version)

            measurements.append(measurement)
            d_job[job_id_res].set_measurement(measurement)

        if all(d_job[job_id].is_extracted() for job_id in d_job):
            break

    return measurements
