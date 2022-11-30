import asyncio
import csv
import datetime
import sys
import uuid
from pathlib import Path
from typing import Dict

import config
from core import pattern_operations, measurement, utils
from core.exceptions import PatternDoesNotExists
from core.measurement import Measurement
from core.sast_job_runner import InQueue, sast_task_runner, OutQueue


async def measure_list_patterns(pattern_id_list: list[int], language: str, tools: list[Dict],
                                pattern_lib_dir: str = config.DEFAULT_TP_LIBRARY_ROOT_DIR, workers: int = 5):
    pattern_lib_dir_path: Path = Path(pattern_lib_dir).resolve()
    print("DEBUG")
    if not pattern_lib_dir_path.is_dir():
        print(f"Specified `{pattern_lib_dir}` is not a folder or does not exists", file=sys.stderr)
        return

    for t in tools:
        t["supported_languages"] = config.load_sast_specific_config(t["name"], t["version"])["supported_languages"]

    tools = list(filter(lambda x: language in x["supported_languages"], tools))

    now = datetime.datetime.now()

    job_list_ids_all_targeted_patterns = []
    for pattern_id in pattern_id_list:
        try:
            job_list_ids = await pattern_operations.start_add_measurement_for_pattern(
                language, tools, pattern_id, now, pattern_lib_dir_path
            )
            job_list_ids_all_targeted_patterns.append(job_list_ids)
        except PatternDoesNotExists as e:
            pattern_id_list.remove(pattern_id)
            print(e, file=sys.stderr)

    tasks: list[asyncio.Task] = []
    for i in range(workers):
        task: asyncio.Task = asyncio.create_task(sast_task_runner(f"SAST Task runner - {i}", InQueue(), OutQueue()))
        tasks.append(task)

    in_queue_has_complete: asyncio.Task = asyncio.create_task(InQueue().join())
    await asyncio.wait([in_queue_has_complete, *tasks],
                       return_when=asyncio.FIRST_COMPLETED)
    if not in_queue_has_complete.done():
        for task in tasks:
            if task.done():
                task.result()

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

    for i, pattern_id in enumerate(pattern_id_list):
        await pattern_operations.save_measurement_for_pattern(
            language, pattern_id, now, job_list_ids_all_targeted_patterns[i], pattern_lib_dir_path
        )

    out_queue_has_complete: asyncio.Task = asyncio.create_task(OutQueue().join())
    await asyncio.wait([out_queue_has_complete], return_when=asyncio.FIRST_COMPLETED)
    print("Pattern Inspection Completed")


async def measure_all_pattern(language: str, tools: list[Dict],
                              pattern_lib_dir: str = config.DEFAULT_TP_LIBRARY_ROOT_DIR, workers: int = 5):
    pattern_lib_dir_path: Path = Path(pattern_lib_dir).resolve()
    if not pattern_lib_dir_path.is_dir():
        print(f"Specified `{pattern_lib_dir}` is not a folder or does not exists", file=sys.stderr)
        return

    lang_lib_dir_path: Path = pattern_lib_dir_path / language
    if not lang_lib_dir_path.is_dir():
        print(f"Specified language folder`{lang_lib_dir_path}` does not exists", file=sys.stderr)
        return

    id_list: list[int] = list(map(lambda d: int(d.name.split("_")[0]), list(lang_lib_dir_path.iterdir())))
    await measure_list_patterns(id_list, language, tools, pattern_lib_dir, workers)


def print_last_measurement_for_all_patterns(tools: list[Dict], language: str, tp_lib_dir: str):
    tp_lib_dir_path: Path = Path(tp_lib_dir).resolve()
    if not tp_lib_dir_path.is_dir():
        print(f"Specified `{tp_lib_dir}` is not a folder or does not exists", file=sys.stderr)
        return

    lang_lib_dir_path: Path = tp_lib_dir_path / language
    if not lang_lib_dir_path.is_dir():
        print(f"Specified language folder`{lang_lib_dir_path}` does not exists", file=sys.stderr)
        return

    id_list: list[int] = list(map(lambda d: int(d.name.split("_")[0]), list(lang_lib_dir_path.iterdir())))
    print_last_measurement_for_pattern_list(tools, language, id_list, tp_lib_dir)


def print_last_measurement_for_pattern_list(tools: list[Dict], language: str, pattern_ids: list[int], tp_lib_dir: str):
    tp_lib_dir_path: Path = Path(tp_lib_dir).resolve()
    if not tp_lib_dir_path.is_dir():
        print(f"Specified `{tp_lib_dir}` is not a folder or does not exists", file=sys.stderr)
        return

    for pattern_id in pattern_ids:
        instance_dir_list_for_pattern: list[Path] = utils.list_pattern_instances_by_pattern_id(
            language, pattern_id, tp_lib_dir_path
        )
        instance_ids: list[int] = list(map(lambda p: int(p.name.split("_")[0]), instance_dir_list_for_pattern))
        for instance_id in instance_ids:
            print(f"Measurement for: Pattern {pattern_id} Instance {instance_id}")
            for tool in tools:
                print(measurement.load_last_measurement_for_tool(tool, language, tp_lib_dir_path, pattern_id,
                                                                 instance_id))


def export_to_file_last_measurement_for_all_patterns(tools: list[Dict], language: str, tp_lib_dir: str):
    tp_lib_dir_path: Path = Path(tp_lib_dir).resolve()
    if not tp_lib_dir_path.is_dir():
        print(f"Specified `{tp_lib_dir}` is not a folder or does not exists", file=sys.stderr)
        return

    lang_lib_dir_path: Path = tp_lib_dir_path / language
    if not lang_lib_dir_path.is_dir():
        print(f"Specified language folder`{lang_lib_dir_path}` does not exists", file=sys.stderr)
        return

    id_list: list[int] = list(map(lambda d: int(d.name.split("_")[0]), list(lang_lib_dir_path.iterdir())))
    export_to_file_last_measurement_for_pattern_list(tools, language, id_list, tp_lib_dir)


def export_to_file_last_measurement_for_pattern_list(tools: list[Dict], language: str, pattern_ids: list[int],
                                                     tp_lib_dir: str):
    tp_lib_dir_path: Path = Path(tp_lib_dir).resolve()
    pattern_ids = sorted(pattern_ids)
    report_name: str = f"measurement_{language}_{pattern_ids[0]}_{pattern_ids[-1]}_{str(uuid.uuid4())[:4]}.csv"
    report_path_dir: Path = config.RESULT_DIR / "reports"
    report_path_dir.mkdir(parents=True, exist_ok=True)
    if not tp_lib_dir_path.is_dir():
        print(f"Specified `{tp_lib_dir}` is not a folder or does not exists", file=sys.stderr)
        return

    report = open(report_path_dir / report_name, "w")
    fields = ["pattern_id", "instance_id", "pattern_name", "language", "tool", "results", "negative_test_case"]
    writer = csv.DictWriter(report, fieldnames=fields)
    writer.writeheader()
    for pattern_id in pattern_ids:
        instance_dir_list_for_pattern: list[Path] = utils.list_pattern_instances_by_pattern_id(
            language, pattern_id, tp_lib_dir_path
        )
        instance_ids: list[int] = list(map(lambda p: int(p.name.split("_")[0]), instance_dir_list_for_pattern))
        for instance_id in instance_ids:
            for tool in tools:
                meas: Measurement = measurement.load_last_measurement_for_tool(
                    tool, language, tp_lib_dir_path, pattern_id, instance_id
                )
                writer.writerow({
                    "pattern_id": meas.instance.pattern_id,
                    "instance_id": meas.instance.instance_id,
                    "pattern_name": meas.instance.name,
                    "language": language,
                    "tool": f"{meas.tool}:{meas.version}",
                    "results": "YES" if meas.result else "NO",
                    "negative_test_case": "YES" if meas.instance.properties_negative_test_case else "NO"
                })
