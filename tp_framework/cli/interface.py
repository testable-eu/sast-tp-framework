import asyncio
import json
from pathlib import Path
from typing import Dict

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

import config
from core import utils, pattern_operations, measurement, discovery, measure, errors
from core.exceptions import PatternValueError


# CRUD patterns
# TODO - add_pattern: develop UPDATE, DELETE, READ (maybe this one we do not need)...
## CREATE/ADD
def add_pattern(pattern_dir: str, language: str, measure: bool, tools: list[Dict], pattern_json: str = None,
                tp_lib_path: Path = Path(config.DEFAULT_TP_LIBRARY_ROOT_DIR).resolve()):
    # TODO - add_pattern: add some printing message for the user
    pattern_dir_path: Path = Path(pattern_dir).resolve()
    if not pattern_dir_path.is_dir():
        print(errors.patternFolderNotFound(pattern_dir_path))
        return

    if not pattern_json:
        # TODO - add_pattern: we could automatically find the json file
        default_pattern_json = f"{pattern_dir_path.name}.json"
        pattern_json_path: Path = pattern_dir_path / default_pattern_json
        if not pattern_json_path.exists():
            print(errors.patternDefaultJSONNotFound(default_pattern_json))
            return
    else:
        # TODO - add_pattern: handle for both branches the case in which the json file does not exist?
        pattern_json_path: Path = Path(pattern_json).resolve()

    tp_lib_path.mkdir(exist_ok=True, parents=True)

    try:
        created_pattern_path: Path = pattern_operations.add_testability_pattern_to_lib_from_json(
            language,
            pattern_json_path,
            pattern_dir_path,
            tp_lib_path
        )
        created_pattern_id: int = utils.get_id_from_name(created_pattern_path.name)
    except PatternValueError as e:
        print(e)
        raise
    except json.JSONDecodeError as e:
        print(errors.patternJSONDecodeError())
        raise
    except Exception as e:
        logger.exception(e)
        print(errors.unexpectedException(e))
        raise

    if measure:
        asyncio.run(measure_list_patterns([created_pattern_id], language, tools=tools, tp_lib_path=tp_lib_path))


# Discovery
def run_discovery_for_pattern_list(src_dir: Path, pattern_id_list: list[int], language: str, itools: list[Dict],
                                   tp_lib_path: Path = Path(config.DEFAULT_TP_LIBRARY_ROOT_DIR).resolve(),
                                   output_dir: Path = Path(config.RESULT_DIR).resolve(),
                                   ignore: bool = False):
    print("Discovery for patterns started...")
    # Set output directory and logger
    build_name, disc_output_dir = utils.get_operation_build_name_and_dir(
        "discovery", src_dir, language, output_dir)
    utils.add_loggers(disc_output_dir)
    #
    utils.check_tp_lib(tp_lib_path)
    d_res = discovery.discovery(Path(src_dir), pattern_id_list, tp_lib_path, itools, language, build_name,
                                disc_output_dir, ignore=ignore)
    print("Discovery for patterns completed.")
    print(f"- results available here: {disc_output_dir}")
    print(f"- log file available here: {disc_output_dir / config.logfile}")
    ignored = len(d_res["ignored_not_measured_patterns_ids"])
    if ignored > 0:
        print(f"- discovery failed for {ignored} patterns: {d_res['ignored_not_measured_patterns_ids']}")


def manual_discovery(src_dir: str, discovery_method: str, discovery_rule_list: list[str], language: str,
                     timeout_sec: int = 0, output_dir: Path = Path(config.RESULT_DIR).resolve()):
    print("Execution of specific discovery rules started...")
    # Set output directory and logger
    build_name, disc_output_dir = utils.get_operation_build_name_and_dir(
        "manual_discovery", src_dir, language, output_dir)
    utils.add_loggers(disc_output_dir)
    #
    discovery_rules_to_run = utils.get_discovery_rules(discovery_rule_list, utils.get_discovery_rule_ext(discovery_method))
    src_dir_path: Path = Path(src_dir).resolve()
    d_res = discovery.manual_discovery(src_dir_path, discovery_method, discovery_rules_to_run, language,
                                                      build_name, disc_output_dir, timeout_sec=timeout_sec)
    print("Execution of specific discovery rules completed.")
    print(f"- results available here: {disc_output_dir}")
    print(f"- log file available here: {disc_output_dir / config.logfile}")
    failures = len(d_res["failed_discovery_rules"])
    if failures > 0:
        print(f"- these {failures} discovery rules failed: {d_res['failed_discovery_rules']}")


# SAST Measurement
async def measure_list_patterns(l_pattern_id: list[int], language: str,
                                tools: list[Dict] = config.SAST_TOOLS_ENABLED,
                                tp_lib_path: Path = Path(config.DEFAULT_TP_LIBRARY_ROOT_DIR).resolve(),
                                output_dir: Path = Path(config.RESULT_DIR).resolve(),
                                workers: int = config.WORKERS):
    print("Measuring patterns with SAST started...")
    build_name, meas_output_dir = utils.get_operation_build_name_and_dir(
        "measurement", None, language, output_dir)
    utils.add_loggers(meas_output_dir)
    d_res = await measure.measure_list_patterns(
        l_pattern_id, language, tools, tp_lib_path, meas_output_dir, workers)
    print("Measuring patterns with SAST completed.")
    print(f"- measurement results available here: {d_res['measurement_dir']}")
    print(f"--- measured patterns ids: {d_res['measured_patterns_ids']}")
    print(f"--- not measured patterns ids: {d_res['not_measured_patterns_ids']}")
    print(f"- SAST tool results available here: {meas_output_dir}")
    print(f"- log file available here: {meas_output_dir / config.logfile}")


def report_sast_measurement_for_pattern_list(tools: list[Dict], language: str, pattern_ids: list[int],
                                             tp_lib_path: Path = Path(config.DEFAULT_TP_LIBRARY_ROOT_DIR).resolve(),
                                             export_file: Path = None,
                                             output_dir: Path = Path(config.RESULT_DIR).resolve(),
                                             only_last_measurement: bool = True):
    # TODO: add implementation for only_last_measurement=False
    print("Reporting for SAST measurement results started...")
    output_dir.mkdir(exist_ok=True, parents=True)
    utils.add_loggers(output_dir)
    results = []
    for pattern_id in pattern_ids:
        instance_dir_list_for_pattern: list[Path] = utils.list_pattern_instances_by_pattern_id(
            language, pattern_id, tp_lib_path
        )
        instance_ids: list[int] = list(map(lambda p: utils.get_id_from_name(p.name), instance_dir_list_for_pattern))

        for instance_id in instance_ids:
            for tool in tools:
                meas: measurement.Measurement = measurement.load_last_measurement_for_tool(
                    tool, language, tp_lib_path, pattern_id, instance_id
                )
                row = {
                    "pattern_id": meas.instance.pattern_id,
                    "instance_id": meas.instance.instance_id,
                    "pattern_name": meas.instance.name,
                    "language": language,
                    "tool": f"{meas.tool}:{meas.version}",
                    "results": "YES" if meas.result else "NO",
                    "negative_test_case": "YES" if meas.instance.properties_negative_test_case else "NO"
                }
                results.append(row)
    header = ["pattern_id", "instance_id", "pattern_name", "language", "tool", "results", "negative_test_case"]
    utils.report_results(results, output_dir, header, export_file=export_file)
    print("")
    print("Reporting for SAST measurement results completed.")
    print(f"- results available here: {output_dir}")
    if export_file:
        print(f"- csv file available here: {output_dir / export_file}")
    print(f"- log file available here: {output_dir / config.logfile}")


def check_discovery_rules(language: str, pattern_ids: list[int],
                          timeout_sec: int,
                          tp_lib_path: Path = Path(config.DEFAULT_TP_LIBRARY_ROOT_DIR).resolve(),
                          export_file: Path = None,
                          output_dir: Path = Path(config.RESULT_DIR).resolve()):
    print("Check/Test discovery rules for patterns started...")
    utils.check_tp_lib(tp_lib_path)
    output_dir.mkdir(exist_ok=True, parents=True)
    utils.add_loggers(output_dir)
    results = discovery.check_discovery_rules(language, pattern_ids,
                          timeout_sec,
                          tp_lib_path,
                          output_dir)
    header = discovery.get_check_discovery_rule_result_header()
    utils.report_results(results, output_dir, header, export_file=export_file)
    print("")
    print("Check/Test discovery rules for patterns completed.")
    print(f"- results available here: {output_dir}")
    if export_file:
        print(f"- csv file available here: {output_dir / export_file}")
    print(f"- log file available here: {output_dir / config.logfile}")