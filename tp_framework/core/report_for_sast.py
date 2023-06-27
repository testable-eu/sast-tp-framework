from pathlib import Path
from typing import Dict

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

import config
from core import utils, measurement
from core.exceptions import InstanceDoesNotExists, MeasurementNotFound
from core.pattern import Pattern
from core.instance import Instance


def report_sast_measurement_for_pattern_list(tools: list[Dict], language: str, l_tp_id: list[int],
                                             tp_lib_path: Path = Path(config.DEFAULT_TP_LIBRARY_ROOT_DIR).resolve(),
                                             export_file: Path = None,
                                             output_dir: Path = Path(config.RESULT_DIR).resolve(),
                                             only_last_measurement: bool = True):
    output_dir.mkdir(exist_ok=True, parents=True)
    utils.add_loggers(output_dir)
    results = []
    for tp_id in l_tp_id:
        target_pattern = Pattern.init_from_id_and_language(tp_id, language, tp_lib_path)
        instance: Instance
        for instance in target_pattern.instances:
            tpi_id = instance.instance_id
            msgpre = f"{language} pattern {tp_id} instance {tpi_id} - "
            logger.info(f"{msgpre}Fetching last measurements...")
            for tool in tools:
                meas = None
                row = {
                    "pattern_id": tp_id,
                    "instance_id": tpi_id,
                    "pattern_name": None,
                    "language": language,
                    "tool": f"{tool['name']}:{tool['version']}",
                    "results": "NOT_FOUND",
                    "negative_test_case": None,
                    "expectation": None
                }
                try:
                    meas: measurement.Measurement = measurement.load_last_measurement_for_tool(
                        tool, language, tp_lib_path, target_pattern, instance
                        )
                except InstanceDoesNotExists:
                    row["results"] = "PATTERN_INSTANCE_DOES_NOT_EXIST"
                except MeasurementNotFound:
                    row["pattern_name"] = instance.name
                    row["results"] = "NOT_FOUND"
                    row["negative_test_case"] = "YES" if instance.properties_negative_test_case else "NO"
                    row["expectation"] = instance.expectation_expectation
                if meas:
                    row["pattern_name"] = meas.instance.name
                    row["tool"] = f"{meas.tool}:{meas.version}" # rewrite `saas` occurrences with precise versions
                    row["results"] = "YES" if meas.result else "NO"
                    row["negative_test_case"] = "YES" if meas.instance.properties_negative_test_case else "NO"
                    row["expectation"] = meas.expected_result
                results.append(row)
    logger.info(f"Measurements fetched. Creating report...")
    header = ["pattern_id", "instance_id", "pattern_name", "language", "tool", "results", "expectation", "negative_test_case"]
    utils.report_results(results, output_dir, header, export_file=export_file)
    logger.info(f"Report created.")
