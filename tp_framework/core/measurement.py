from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Dict
import sast.utils as sast_utils

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

import config
from core import utils
from core.exceptions import MeasurementNotFound, MeasurementInvalid
from core.instance import Instance


class Measurement:
    def __init__(self,
                 date: datetime = None,
                 result: bool = None,
                 expected_result: bool = None,
                 tool: str = None,
                 version: str = None,
                 instance: Instance = None
                 ):
        self.date = date
        self.result = result
        self.expected_result = expected_result
        self.tool = tool
        self.version = version
        self.instance = instance
    
    #TODO: TESTING
    @classmethod
    def init_from_measurement_dict(cls, meas_dict):
        return cls()._init_from_dict(meas_dict)

    def _init_from_dict(self, dict_to_init_from: dict):
        try:
            self.date = dict_to_init_from["date"]
            self.result = dict_to_init_from["result"]
            self.tool = dict_to_init_from["tool"]
            self.version = dict_to_init_from["version"]
        except KeyError as e:
            raise MeasurementInvalid(e)
        return self

    def define_verdict(self, date: datetime, instance: Instance, findings: list[Dict], tool: str, version: str,
                       sink_line_strict : bool = False,
                       sink_file_strict : bool = True) -> Measurement:
        date_time_str = date.strftime("%Y-%m-%d %H:%M:%S")
        self.date = date_time_str
        found = False
        for finding in findings:
            c_type = (instance.expectation_type == finding["type"])
            c_sink_file = not instance.expectation_sink_file or (instance.expectation_sink_file.name == finding["file"])
            c_sink_line = not instance.expectation_sink_line or (instance.expectation_sink_line == int(finding["line"]))
            # logger debug
            logger.debug(
                f"Pattern {instance.pattern_id} instance {instance.instance_id} - Verdict condition - type: {c_type} [exp: {instance.expectation_type}, finding: {finding['type']}]")
            if instance.expectation_sink_file:
                logger.debug(
                    f"Pattern {instance.pattern_id} instance {instance.instance_id} - Verdict condition - sink file: {c_sink_file} [exp: {instance.expectation_sink_file}, finding: {finding['file']}]")
            if instance.expectation_sink_line:
                logger.debug(
                    f"Pattern {instance.pattern_id} instance {instance.instance_id} - Verdict condition - sink line: {c_sink_line} [exp: {instance.expectation_sink_line}, finding: {finding['line']}]")
            #
            found = c_type and (c_sink_file or not sink_file_strict) and (c_sink_line or not sink_line_strict)
            # if instance.expectation_sink_line is not None:
            #     found = (instance.expectation_sink_line == int(finding["line"])) and (instance.expectation_sink_file.name == finding["file"])
            #     if not found:
            #         logger.warning(f"Sink for pattern instance: <{instance.pattern_id}, {instance.name}, {instance.instance_id}> not matching SAST: {tool}:{version} scan findings")
            # else:
            #     found = instance.expectation_sink_file.name == finding["file"]
            if found:
                break # we found a matching finding
        self.result = (found == instance.expectation_expectation)
        self.expected_result = instance.expectation_expectation
        self.tool = tool
        self.version = version
        self.instance = instance
        return self

    def __lt__(self, other):
        return self.date < other.date

    def __str__(self):
        supported = "YES" if self.result else "NO"
        return f"{self.tool}:{self.version}:{supported}->instance_{self.instance.instance_id}_{self.instance.pattern_id}_{self.instance.name}"

    def __repr__(self):
        return self.__str__()


def load_measurements(meas_file: Path, tp_lib: Path, language: str) -> list[Measurement]:
    try:
        with open(meas_file) as f:
            meas: Dict = json.load(f)
    except Exception as e:
        logger.exception(f"Failed in loading measurement json file {meas_file}. It seems corrupted and it is renamed. Raised exception: {utils.get_exception_message(e)}")
        f.close()
        meas_file.rename(meas_file.with_suffix(".corrupted"))
        return []
    parsed_meas: list[Measurement] = []
    for m in meas:
        instance_json_path = tp_lib / Path(m["instance"])
        instance = Instance.init_from_json_path(instance_json_path, None, language, tp_lib)
        # NOTE 06/2023: if not expectation in measurement, then we take it from instance (backword compatibility though it could introduce mistakes if the instance expectation was changed after the measurement)
        expected_result = m["expected_result"] if "expected_result" in m.keys() else instance.expectation_expectation
        parsed_meas.append(Measurement(
            m["date"],
            m["result"],
            expected_result,
            m["tool"],
            m["version"],
            instance,
        ))
    return parsed_meas


def load_last_measurement_for_tool(tool: Dict, language: str, tp_lib: Path, pattern, 
                                   instance: Instance) -> Measurement:
    # TODO - load last measurement: the code hereafter strongly depends on the folder notation in place for
    #       patterns and pattern instances. Make sure to factorize in function what needs to
    #       and to generalize the approach as much as we can to rely the least possible on
    #       the strict notation
    pattern_dir_name: str = pattern.path.name
    instance_dir_name: str = instance.path.name
    measurement_dir_for_pattern_instance: Path = utils.get_measurement_dir_for_language(tp_lib, language) / pattern_dir_name / instance_dir_name
    if not measurement_dir_for_pattern_instance.is_dir():
        ee = MeasurementNotFound(pattern.pattern_id)
        logger.exception(ee)
        raise ee
    meas_file_list = list(
        filter(lambda p: p.name.startswith("measurement"), measurement_dir_for_pattern_instance.iterdir()))

    measurements: list[Measurement] = []
    for meas_file in meas_file_list:
        measurements.extend(load_measurements(meas_file, tp_lib, language))

    measurements_for_tool: list[Measurement] = list(
        filter(lambda m:
               m.tool == tool["name"] and
               sast_utils.sast_tool_version_match(m.version, tool["version"]),
               measurements)
    )
    if not measurements_for_tool:
        logger.warning(f'No measurement has been found for tool {tool["name"]}:{tool["version"]} on pattern {pattern.pattern_id} instance {instance.instance_id}')
        return None
    return sorted(measurements_for_tool, reverse=True)[0]


def meas_list_to_tp_dict(l_meas: list[Measurement]) -> Dict:
    d_tp_meas = {}
    for meas in l_meas:
        if not meas.instance.pattern_id in d_tp_meas:
            d_tp_meas[meas.instance.pattern_id] = {}
        d_tpi_meas = d_tp_meas[meas.instance.pattern_id]
        if not meas.instance.instance_id in d_tpi_meas:
            d_tpi_meas[meas.instance.instance_id] = []
        d_tpi_meas[meas.instance.instance_id].append(meas)
    return d_tp_meas


def any_tool_matching(meas, tools, version=config.discovery_under_measurement["enforce_tool_version"]):
    if not version:
        return any(meas.tool == tool["name"] for tool in tools)
    else:
        return any(meas.tool == tool["name"] and meas.version == tool["version"] for tool in tools)
