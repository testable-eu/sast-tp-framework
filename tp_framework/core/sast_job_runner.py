import asyncio
import uuid
from typing import Dict

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

from core.measurement import Measurement

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class InQueue(asyncio.Queue, metaclass=Singleton):
    pass


class OutQueue(asyncio.Queue, metaclass=Singleton):
    pass


async def sast_task_runner(name: str, in_queue: asyncio.Queue, out_queue: asyncio.Queue):
    try:
        while True:
            job_id, tool_name, tool_version, instance, date, task = await in_queue.get()
            try:
                csv_res = await task
                out_queue.put_nowait((job_id, tool_name, tool_version, instance, date, csv_res))
            # asyncio.CancelledError is a part of BaseException
            # https://docs.python.org/3/library/asyncio-exceptions.html
            # Note: if the Exceptions raised in a SAST JOB is not properly handled, it will stop the
            # sast_task_runner (Worker), thus may end up in a situation where the out_queue is empty which will result
            # in waiting indefinitely.
            except (Exception, asyncio.CancelledError) as e:
                out_queue.put_nowait((job_id, tool_name, tool_version, instance, date, None))
                logger.exception(f"{name} exception {e!r}")
                # raise
            finally:
                in_queue.task_done()
    except asyncio.CancelledError:
        raise


class SASTjob:
    def __init__(self, tool: str, tp_id: int=None, tpi_id: int=None, error: bool=False):
        self.job_id = uuid.uuid4()
        self.tp_id = tp_id
        self.tpi_id = tpi_id
        self.tool = tool
        self.error = error
        self.extracted: bool = False
        self.measurement: Measurement = None


    def is_extracted(self) -> bool:
        return self.extracted


    def set_extracted(self, value: bool=True):
        self.extracted = value


    def set_measurement(self, meas: Measurement):
        self.measurement = meas


def job_list_to_dict(l: list[SASTjob]) -> Dict:
    d = {}
    for job in l:
        d[job.job_id] = job
    return d


def get_valid_job_list_for_patterns(d_status: Dict) -> list[SASTjob]:
    return get_specific_job_list_for_patterns(d_status, valid=True)


def get_invalid_job_list_for_patterns(d_status: Dict) -> list[SASTjob]:
    return get_specific_job_list_for_patterns(d_status, valid=False)


def get_specific_job_list_for_patterns(d_status: Dict, valid: bool = True) -> list[SASTjob]:
    l_jobs = []
    for tp_id in d_status:
        l_jobs = l_jobs + get_specific_job_list_for_pattern(d_status[tp_id], valid=valid)
    return l_jobs


def get_specific_job_list_for_pattern(d_tp_status: Dict, valid: bool = True) -> list[SASTjob]:
    l_jobs = []
    for tpi_id in d_tp_status:
        l_jobs = l_jobs + get_specific_job_list_for_pattern_instance(d_tp_status[tpi_id], valid=valid)
    return l_jobs


def get_specific_job_list_for_pattern_instance(l_jobs: list[SASTjob], valid: bool = True):
    return [job for job in l_jobs if valid != job.error]