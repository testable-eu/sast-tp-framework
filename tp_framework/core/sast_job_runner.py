import asyncio

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))


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
            except Exception as e:
                logger.exception(f"{name} exception {e!r}")
                raise e
            finally:
                in_queue.task_done()
    except asyncio.CancelledError:
        raise
