import asyncio
from pathlib import Path
from typing import Dict
from datetime import datetime

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

from core import utils, pattern_operations
from core.exceptions import PatternDoesNotExists
from core.sast_job_runner import sast_task_runner, InQueue, OutQueue

async def measure_list_patterns(l_tp_id: list[int], language: str,
                                tools: list[Dict],
                                tp_lib_path: Path,
                                output_dir: Path,
                                workers: int) -> Dict:
    logger.info(f"Collect jobs to run for SAST tools over patterns: started...")
    utils.check_tp_lib(tp_lib_path)
    ftools = utils.filter_sast_tools(tools, language)
    logger.info(f"SAST tools that will be used for measurement: {ftools}")

    now = datetime.now()
    l_job_t_tpi = []
    l_existing_tp = []
    l_notfound_tp = []
    for i, tp_id in enumerate(l_tp_id):
        logger.info(utils.get_tp_op_status_string(
            (i + 1, len(l_tp_id), tp_id)  # tp_info
        ))
        try:
            job_list_ids = await pattern_operations.start_add_measurement_for_pattern(
                language, ftools, tp_id, now, tp_lib_path, output_dir
            )
            logger.info(f"Collected {len(job_list_ids)} jobs for pattern id {tp_id}.")
            l_job_t_tpi.append(job_list_ids)
            l_existing_tp.append(tp_id)
        except PatternDoesNotExists as e:
            l_notfound_tp.append(tp_id)
            logger.warning(f"Pattern id {tp_id} is not found or its folder is not properly structured, it will not be measured...")
            continue
        logger.info(utils.get_tp_op_status_string(
            (i + 1, len(l_tp_id), tp_id), status="done."
        ))
    logger.info(f"Collected {len(l_job_t_tpi)} jobs to run for SAST tools over patterns: completed.")

    logger.info(f"Create SAST jobs: started...")
    tasks: list[asyncio.Task] = []
    for numw in range(workers):
        task: asyncio.Task = asyncio.create_task(sast_task_runner(f"SAST Task runner - {numw}", InQueue(), OutQueue()))
        tasks.append(task)
    logger.info(f"Create SAST jobs: done.")

    logger.info(f"Run SAST jobs: started...")
    in_queue_has_complete: asyncio.Task = asyncio.create_task(InQueue().join())
    await asyncio.wait([in_queue_has_complete, *tasks],
                       return_when=asyncio.FIRST_COMPLETED)
    if not in_queue_has_complete.done():
        for task in tasks:
            try:
                if task.done():
                    task.result()
            except Exception as e:
                logger.warning(f"Failed in executing SAST task in queue. This will be ignored and execution continued. Exception raised: {utils.get_exception_message(e)}")
                continue
    for task in tasks:
        try:
            task.cancel()
        except Exception as e:
            logger.warning(
                f"Failed in cancelling executed SAST task. This will be ignored and execution continued. Exception raised: {utils.get_exception_message(e)}")
            continue
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info(f"Run SAST jobs: done.")

    logger.info(f"Save SAST tools measurement results: started...")
    for numw, tp_id in enumerate(l_existing_tp):
        await pattern_operations.save_measurement_for_pattern(
            language, tp_id, now, l_job_t_tpi[numw], tp_lib_path
        )

    out_queue_has_complete: asyncio.Task = asyncio.create_task(OutQueue().join())
    await asyncio.wait([out_queue_has_complete], return_when=asyncio.FIRST_COMPLETED)
    logger.info(f"Save SAST tools measurement results: completed.")
    d_results = {
        "measurement_dir": str(utils.get_measurement_dir_for_language(tp_lib_path, language)),
        "measured_patterns_ids": l_existing_tp,
        "not_measured_patterns_ids": l_notfound_tp
    }
    return d_results
