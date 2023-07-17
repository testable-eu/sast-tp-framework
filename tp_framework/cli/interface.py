import asyncio
import json
from pathlib import Path
from typing import Dict

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

import config
from core import utils, pattern_operations, discovery, measure, errors, report_for_sast
from core.exceptions import PatternInvalid, AddPatternError
from core.pattern import Pattern


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

    pattern_json_path = Path(pattern_json) if pattern_json else utils.get_json_file(pattern_dir_path)
    if not pattern_json_path:
        print(errors.patternDefaultJSONNotFound(pattern_dir))
        return
    
    tp_lib_path.mkdir(exist_ok=True, parents=True)

    try:
        created_pattern: Pattern = pattern_operations.add_testability_pattern_to_lib_from_json(
            language,
            pattern_json_path,
            pattern_dir_path,
            tp_lib_path
        )
    except (PatternInvalid, AddPatternError) as e:
        print(e)
        raise
    except Exception as e:
        logger.exception(e)
        print(errors.unexpectedException(e))
        raise

    if measure:
        asyncio.run(measure_list_patterns([created_pattern.pattern_id], language, tools=tools, tp_lib_path=tp_lib_path))


# Discovery
def run_discovery_for_pattern_list(src_dir: Path, pattern_id_list: list[int], language: str, itools: list[Dict],
                                   tp_lib_path: Path = Path(config.DEFAULT_TP_LIBRARY_ROOT_DIR).resolve(),
                                   output_dir: Path = Path(config.RESULT_DIR).resolve(),
                                   ignore: bool = False,
                                   cpg: str = None):
    print("Discovery for patterns started...")
    # Set output directory and logger
    build_name, disc_output_dir = utils.get_operation_build_name_and_dir(
        "discovery", src_dir, language, output_dir)
    utils.add_loggers(disc_output_dir)
    #
    utils.check_tp_lib(tp_lib_path)
    d_res = discovery.discovery(Path(src_dir), pattern_id_list, tp_lib_path, itools, language, build_name,
                                disc_output_dir, ignore=ignore, cpg=cpg)
    print("Discovery for patterns completed.")
    print(f"- results available here: {disc_output_dir}")
    print(f"- log file available here: {disc_output_dir / config.logfile}")
    if ignore:
        print(f"- SAST measurement: ignored")
    else:
        print(f"- SAST measurement: considered")
        l_ign_tp = discovery.get_ignored_tp_from_results(d_res)
        l_ign_tpi = discovery.get_ignored_tpi_from_results(d_res, "not_found")
        l_ign_tpi_as_supported = discovery.get_ignored_tpi_from_results(d_res, "supported")
        print(f"  - measurement not found for {len(l_ign_tp)} patterns: {l_ign_tp}")
        print(f"  - measurement not found for {len(l_ign_tpi)} pattern instances: {l_ign_tpi}")
        print(f"  - discovery skipped for {len(l_ign_tpi_as_supported)} pattern instances as supported by SAST tools: {l_ign_tpi_as_supported}")
    
    l_tpi_unsucc_dr = discovery.get_unsuccessful_discovery_tpi_from_results(d_res)
    l_tpi_succ_dr = discovery.get_successful_discovery_tpi_from_results(d_res)
    nfindings = discovery.get_num_discovery_findings_from_results(d_res)
    print(f"- discovery rules:")
    print(f"  - not working for {len(l_tpi_unsucc_dr)} pattern instances: {l_tpi_unsucc_dr}")
    print(f"  - successful for {len(l_tpi_succ_dr)} pattern instances")
    print(f"  - {nfindings} occurrences of pattern instances discovered")


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
    print(f"- SAST tool results available here: {meas_output_dir}")
    print(f"--- {len(d_res['sast_job_execution_valid'])} SAST jobs run successfully")
    if d_res['sast_job_collection_error']:
        print(f"--- {len(d_res['sast_job_collection_error'])} errors in collecting SAST jobs")
    if d_res['sast_job_execution_error']:
        print(f"--- {len(d_res['sast_job_execution_error'])} errors in executing SAST jobs")
    print(f"- log file available here: {meas_output_dir / config.logfile}")


def report_sast_measurement_for_pattern_list(tools: list[Dict], language: str, pattern_ids: list[int],
                                             tp_lib_path: Path = Path(config.DEFAULT_TP_LIBRARY_ROOT_DIR).resolve(),
                                             export_file: Path = None,
                                             output_dir: Path = Path(config.RESULT_DIR).resolve(),
                                             only_last_measurement: bool = True):
    # TODO: add implementation for only_last_measurement=False
    print("Reporting for SAST measurement results started...")
    report_for_sast.report_sast_measurement_for_pattern_list(tools, language, pattern_ids,
                                                             tp_lib_path=tp_lib_path, export_file=export_file,
                                                             output_dir=output_dir,
                                                             only_last_measurement=only_last_measurement)
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
    d_res = discovery.check_discovery_rules(language, pattern_ids,
                          timeout_sec,
                          tp_lib_path,
                          output_dir)
    results = d_res["results"]
    header = discovery.get_check_discovery_rule_result_header()
    utils.report_results(results, output_dir, header, export_file=export_file)
    print("")
    print("Check/Test discovery rules for patterns completed.")
    print(f"- results available here: {output_dir}")
    print(f"  - num successful (discovery rule was run): {d_res['counters']['successful']}")
    print(f"  - num unsuccessful (discovery rule was run): {d_res['counters']['unsuccessful']}")
    print(f"  - num missing (no discovery rule): {d_res['counters']['missing']}")
    print(f"  - num errors: {d_res['counters']['errors']}")
    if export_file:
        print(f"- csv file available here: {output_dir / export_file}")
    print(f"- log file available here: {output_dir / config.logfile}")


def repair_patterns(language: str, pattern_ids: list,
                    masking_file: Path, include_README: bool,
                    measurement_results: Path, checkdiscoveryrule_results: Path,
                    output_dir: Path, tp_lib_path: Path):
    print("Pattern Repair started...")
    should_include_readme = not include_README
    utils.check_tp_lib(tp_lib_path)
    if should_include_readme:
        utils.check_file_exist(checkdiscoveryrule_results)
        utils.check_file_exist(masking_file, ".json") if masking_file else None
        utils.check_measurement_results_exist(measurement_results)
    output_dir.mkdir(exist_ok=True, parents=True)
    utils.add_loggers(output_dir)

    for tp_id in pattern_ids:
        try:
            pattern =  Pattern.init_from_id_and_language(tp_id, language, tp_lib_path)
        except PatternInvalid as e:
            print(f"Failed to init pattern: {tp_id} due to {e}")
            continue
        pattern.repair(should_include_readme, 
                       discovery_rule_results=checkdiscoveryrule_results,
                       measurement_results=measurement_results,
                       masking_file=masking_file)