from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Dict

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

from core import utils
from core.exceptions import InstanceDoesNotExists, MeasurementNotFound
from core.instance import Instance, load_instance_from_metadata


class Measurement:
    def __init__(self,
                 date: datetime = None,
                 result: bool = None,
                 tool: str = None,
                 version: str = None,
                 instance: Instance = None
                 ):
        self.date = date
        self.result = result
        self.tool = tool
        self.version = version
        self.instance = instance

    def define_verdict(self, date: datetime, instance: Instance, finding: Dict, tool: str, version: str) -> Measurement:
        date_time_str = date.strftime("%Y-%m-%d %H:%M:%S")
        self.date = date_time_str
        # TODO: it should be checking for the expectation!
        if not finding:
            self.result = False
        elif instance.expectation_sink_line is not None:
            self.result = (instance.expectation_sink_line == int(finding["line"])) and (
                    instance.expectation_sink_file.name == finding["file"])
            if not self.result:
                print(f"WARNING: Sink for pattern instance: <{instance.pattern_id}, {instance.name}, {instance.instance_id}> not matching SAST: {tool}:{version} scan findings")
        else:
            self.result = instance.expectation_sink_file.name == finding["file"]

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


def load_from_metadata(file: Path, language: str) -> list[Measurement]:
    with open(file) as f:
        meas: Dict = json.load(f)

    parsed_meas: list[Measurement] = []
    for m in meas:
        instance = load_instance_from_metadata(m["instance"], file.parents[4], language)
        parsed_meas.append(Measurement(
            m["date"],
            m["result"],
            m["tool"],
            m["version"],
            instance,
        ))

    return parsed_meas


def load_last_measurement_for_tool(tool: Dict, language: str, tp_lib_dir: Path, pattern_id: int,
                                   instance_id: int) -> Measurement:
    # TODO: the code hereafter strongly depends on the folder notation in place for
    #       patterns and pattern instances. Make sure to factorize in function what needs to
    #       and to generalize the approach as much as we can to rely the least possible on
    #       the strict notation
    pattern_dir: Path = utils.get_pattern_dir_from_id(pattern_id, language, tp_lib_dir)
    pattern_dir_name: str = pattern_dir.name
    instance_dir_name: str = f"{instance_id}_instance_{pattern_dir_name}"
    instance_dir: Path = pattern_dir / instance_dir_name
    if not instance_dir.is_dir():
        ee = InstanceDoesNotExists(instance_id=instance_id)
        logger.exception(ee)
        raise ee
    measurement_dir_for_pattern_instance: Path = utils.get_measurement_dir_for_language(tp_lib_dir, language) / pattern_dir_name / instance_dir_name
    if not measurement_dir_for_pattern_instance.is_dir():
        ee = MeasurementNotFound(pattern_id)
        logger.exception(ee)
        raise ee
    meas_file_list = list(
        filter(lambda p: p.name.startswith("measurement"), measurement_dir_for_pattern_instance.iterdir()))

    measurements: list[Measurement] = []
    for meas_file in meas_file_list:
        measurements.extend(load_from_metadata(meas_file, language))

    # TODO: this looks like requiring improvements...
    #       - hardcoded on the "." separator??
    #       - it seems to assume always a 3 numbers in a version???
    measurements_for_tool: list[Measurement] = list(
        filter(lambda m:
               m.tool == tool["name"] and
               m.version.split(".")[0] == tool["version"].split(".")[0] and
               m.version.split(".")[1] == tool["version"].split(".")[1] and
               m.version.split(".")[2] == tool["version"].split(".")[2],
               measurements)
    )
    return sorted(measurements_for_tool, reverse=True)[0]


