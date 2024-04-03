import asyncio
from pathlib import Path
from typing import Dict
from datetime import datetime

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

from core import utils, pattern_operations
from core.exceptions import PatternDoesNotExists
from core.sast_job_runner import sast_task_runner, InQueue, OutQueue, \
    get_valid_job_list_for_patterns, get_invalid_job_list_for_patterns, SASTjob

import sast.utils as sast_utils

async def measure_list_patterns(l_tp_id: list[int], language: str,
                                tools: list[Dict],
                                tp_lib_path: Path,
                                output_dir: Path,
                                workers: int) -> Dict:
    logger.info(f"SAST measurement - started...")
    utils.check_tp_lib(tp_lib_path)
    ftools = sast_utils.filter_sast_tools(tools, language)
    logger.info(f"SAST measurement - tools: {ftools}")
    logger.info(f"SAST measurement - collect jobs to run: started...")
    now = datetime.now()
    d_status = {}
    for i, tp_id in enumerate(l_tp_id):
        logger.info(utils.get_tp_op_status_string(
            (i + 1, len(l_tp_id), tp_id)  # tp_info
        ))
        try:
            d_status[tp_id] = await pattern_operations.start_add_measurement_for_pattern(
                language, ftools, tp_id, now, tp_lib_path, output_dir
            )
        except PatternDoesNotExists as e:
            d_status[tp_id] = {}
            logger.warning(f"SAST measurement - pattern {tp_id} not found or its folder not properly structured. It will be ignored...")
            continue
        logger.info(utils.get_tp_op_status_string(
            (i + 1, len(l_tp_id), tp_id), status="done."
        ))

    l_job_l_t_tpi: list[SASTjob] = get_valid_job_list_for_patterns(d_status)
    l_job_invalid: list[SASTjob] = get_invalid_job_list_for_patterns(d_status)
    logger.info(f"SAST measurement - collected {len(l_job_l_t_tpi)} jobs to run.")
    if l_job_invalid:
        logger.warning(f"SAST measurement - some jobs failed in being collected.")
        logger.debug(f"SAST measurement - available info on invalid jobs: {l_job_invalid}")

    tasks: list[asyncio.Task] = []
    for i in range(workers):
        task: asyncio.Task = asyncio.create_task(sast_task_runner(f"SAST Task runner - {i}", InQueue(), OutQueue()))
        tasks.append(task)
    logger.info(f"SAST measurement - created {workers} worker tasks to execute the SAST jobs")

    logger.info(f"SAST measurement - run SAST jobs with workers: started...")
    in_queue_has_complete: asyncio.Task = asyncio.create_task(InQueue().join())
    await asyncio.wait([in_queue_has_complete, *tasks],
                       return_when=asyncio.FIRST_COMPLETED)
    if not in_queue_has_complete.done():
        for task in tasks:
            try:
                if task.done():
                    task.result()
            except Exception as e:
                logger.warning(f"SAST measurement - failed in executing a SAST task in queue. This will be ignored. Exception raised: {utils.get_exception_message(e)}")
                continue
    for task in tasks:
        try:
            task.cancel()
        except Exception as e:
            logger.warning(
                f"SAST measurement - failed in cancelling executed SAST task. This will be ignored. Exception raised: {utils.get_exception_message(e)}")
            continue
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info(f"SAST measurement - run SAST jobs with workers: done.")

    logger.info(f"SAST measurement - save results: started...")
    await pattern_operations.save_measurement_for_patterns(
            language, now, l_job_l_t_tpi, tp_lib_path
    )

    out_queue_has_complete: asyncio.Task = asyncio.create_task(OutQueue().join())
    await asyncio.wait([out_queue_has_complete], return_when=asyncio.FIRST_COMPLETED)
    logger.info(f"SAST measurement - save results: completed.")
    #########
    # stats
    l_coll_error = []
    l_sast_error = []
    l_valid = []
    for tp_id in d_status:
        if not d_status[tp_id]:
            l_coll_error.append((tp_id, "all", "all"))
            continue
        for tpi_id in d_status[tp_id]:
            if not d_status[tp_id][tpi_id]:
                l_coll_error.append((tp_id, tpi_id, "all"))
                continue
            for job in d_status[tp_id][tpi_id]:
                if job.error:
                    l_coll_error.append((tp_id, tpi_id, job.tool))
                elif not job.measurement:
                    l_sast_error.append((tp_id, tpi_id, job.tool))
                else:
                    l_valid.append((tp_id, tpi_id, job.tool))
    if l_coll_error:
        logger.info(f"SAST measurement - {len(l_coll_error)} errors in collecting sast jobs")
        logger.debug(f"SAST measurement - {len(l_coll_error)} errors in collecting sast jobs (tp_id, tpi_id, tool): {l_coll_error}")
    if l_sast_error:
        logger.info(f"SAST measurement - {len(l_sast_error)} errors in executing sast jobs")
        logger.debug(f"SAST measurement - {len(l_sast_error)} errors in executing sast jobs (tp_id, tpi_id, tool): {l_sast_error}")
    logger.info(f"SAST measurement - {len(l_valid)} sast jobs run successfully")
    # TODO: what about SAST results expectations?
    d_results = {
        "measurement_dir": str(utils.get_measurement_dir_for_language(tp_lib_path, language)),
        "measurement_results": d_status,
        "sast_job_collection_error": l_coll_error,
        "sast_job_execution_error": l_sast_error,
        "sast_job_execution_valid": l_valid
    }
    logger.info(f"SAST measurement - done")
    return d_results
