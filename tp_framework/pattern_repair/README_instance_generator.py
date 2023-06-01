import logging
import re
from os import path
from datetime import datetime

from pattern_repair.utils import (
    read_json,
    get_dict_keys,
    translate_bool,
    get_language_by_file_ending,
    get_instance_name,
    get_files_with_ending,
    read_file,
)
from pattern_repair.README_markdown_elements import *

from core import loggermgr

logger = logging.getLogger(loggermgr.logger_name(__name__))


class InstanceREADMEGenerator:
    def __init__(
        self,
        path_to_pattern: str,
        language: str,
        path_to_pattern_measurements: str,
        instance_jsons: list[str],
        level: int = 2,
        masking_file: str = "mask.json",
    ) -> None:
        self.language = language.upper()
        self.log_prefix = "Generating README: "
        self.pattern_path = path_to_pattern
        self.level = level
        self.pattern_measurements = (
            path_to_pattern_measurements if path_to_pattern_measurements else ""
        )

        self.instances_jsons = instance_jsons
        self.has_multiple_instances = len(self.instances_jsons) > 1
        self.instance_dicts = [read_json(i_path) for i_path in self.instances_jsons]

        self.current_instance = None
        self.current_instance_dict = None
        self.current_instance_dict_keys = None

        self.instance_structure = [
            self._instance_name,
            self._instance_description,
            self._instance_code,
            self._instance_properties,
            self._instance_more,
        ]
        self.instance_more_structure = [
            self._compile,
            self._discovery,
            self._measurement,
            self._remediation,
        ]

        self.mask = {}
        if masking_file and path.isfile(masking_file):
            self.mask = read_json(masking_file)
        elif masking_file:
            logger.info(f"Could not file the provided masking file: {masking_file}")

    def _instance_name(self) -> list:
        """Generates the Markdown heading for the current instance."""
        return [MarkdownHeading(get_instance_name(self.current_instance), self.level)]

    def _instance_description(self) -> list:
        """Generates the description for the current instance."""
        desc = (
            self.current_instance_dict["description"]
            if "description" in self.current_instance_dict_keys
            else ""
        )
        content = self._get_file_content_if_exists(desc, debug_name="description")
        return [MarkdownString(content)] if content else []

    def _instance_code(self) -> list:
        """Generates the Instance code for the current instance."""
        heading = MarkdownHeading("Code", self.level + 1)
        code = (
            self.current_instance_dict["code"]["path"]
            if "code:path" in self.current_instance_dict_keys
            else ""
        )
        source = (
            self.current_instance_dict["expectation"]["source_file"]
            if "expectation:source_file" in self.current_instance_dict_keys
            else ""
        )
        sink = (
            self.current_instance_dict["expectation"]["sink_file"]
            if "expectation:sink_file" in self.current_instance_dict_keys
            else ""
        )
        if source == sink:
            content = self._get_file_content_if_exists(code, debug_name="code")
            return [heading, MarkdownCode(content, self.language)] if content else []
        source_content = self._get_file_content_if_exists(
            source, debug_name="source_file"
        )
        sink_content = self._get_file_content_if_exists(sink, debug_name="sink_file")
        return [
            heading,
            MarkdownHeading("Source File", self.level + 2),
            MarkdownCode(source_content, self.language),
            MarkdownHeading("Sink File", self.level + 2),
            MarkdownCode(sink_content, self.language),
        ]

    def _instance_properties(self) -> list:
        """Generates the table of instance properties."""
        properties_dict = {
            "category": [self.current_instance_dict["properties"]["category"]],
            "feature_vs_internal_api": [
                self.current_instance_dict["properties"]["feature_vs_internal_api"]
            ],
            "input_sanitizer": [
                translate_bool(
                    self.current_instance_dict["properties"]["input_sanitizer"]
                )
            ],
            "source_and_sink": [
                translate_bool(
                    self.current_instance_dict["properties"]["source_and_sink"]
                )
            ],
            "negative_test_case": [
                translate_bool(
                    self.current_instance_dict["properties"]["negative_test_case"]
                )
            ],
        }
        return [
            MarkdownHeading("Instance Properties", self.level + 1),
            MarkdownTable(properties_dict),
        ]

    def _instance_more(self) -> list:
        """Generates the 'more' section for an instance."""
        ret = []
        for f in self.instance_more_structure:
            ret += f()
        return [MarkdownCollapsible(ret, MarkdownString("<b>More</b>"))]

    def _compile(self) -> list:
        """Generates the compile section for an instance."""
        compile = (
            self.current_instance_dict["compile"]["binary"]
            if "compile:binary" in self.current_instance_dict_keys
            else ""
        )
        content = self._get_file_content_if_exists(compile, "compile")
        binary = MarkdownCode(content, get_language_by_file_ending(compile))
        return (
            [MarkdownCollapsible([binary], MarkdownHeading("Compile", self.level + 1))]
            if content
            else []
        )

    def _discovery(self) -> list:
        """Generates the 'discovery' section for an instance."""
        desc = (
            self.current_instance_dict["discovery"]["notes"]
            if "discovery:notes" in self.current_instance_dict_keys
            else ""
        )
        desc = MarkdownString(self._get_file_content_if_exists(desc, "discovery notes"))
        rule_path = (
            self.current_instance_dict["discovery"]["rule"]
            if "discovery:rule" in self.current_instance_dict_keys
            else ""
        )
        rule = self._get_file_content_if_exists(rule_path, "discovery rule")
        # get only necessary content
        rule = re.sub("@main def main\(name .*{$", "", rule, flags=re.M)
        rule = re.sub("importCpg.*$", "", rule, flags=re.M)
        rule = re.sub("println\(.*\)$", "", rule, flags=re.M)
        rule = re.sub("delete;.*$", "", rule, flags=re.M)
        rule = re.sub(".*}.*$", "", rule)
        rule = "\n".join([l.strip() for l in rule.split("\n")])
        rule = (
            MarkdownCode(rule, get_language_by_file_ending(rule_path))
            if rule_path
            else MarkdownString("No discovery rule yet.")
        )
        discovery_table = {
            "discovery method": [self.current_instance_dict["discovery"]["method"]],
            "expected accuracy": [
                self.current_instance_dict["discovery"]["rule_accuracy"]
            ],
        }
        discovery_table = MarkdownTable(discovery_table)
        return [
            MarkdownCollapsible(
                [desc, rule, discovery_table],
                MarkdownHeading("Discovery", self.level + 1),
            )
        ]

    def _measurement(self) -> list:
        """Generates the 'measurement' section for an instance."""
        if not path.isdir(self.pattern_measurements):
            logger.warning(
                f"{self.log_prefix}Could not generate measurement table, because {self.pattern_measurements} does not exist"
            )
            return []
        instance_measurements = path.join(
            self.pattern_measurements, path.basename(self.current_instance)
        )
        measurement_table = {}
        has_measurement = False
        dates = []
        ground_truth = self.current_instance_dict["expectation"]["expectation"]
        for json_file in get_files_with_ending(instance_measurements, ".json"):
            current_json = read_json(json_file)
            for c_dict in current_json:
                has_measurement = True
                tool = f'1::{self.mask[c_dict["tool"].lower()] if c_dict["tool"].lower() in self.mask.keys() else c_dict["tool"]}'
                date = datetime.strptime(c_dict["date"], "%Y-%m-%d %H:%M:%S").strftime(
                    "%d %b %Y"
                )
                dates += [date]
                sast_tool_result = translate_bool(not (c_dict["result"] ^ ground_truth))
                try:
                    measurement_table[tool] += [(sast_tool_result, date)]
                    measurement_table[tool] = sorted(
                        measurement_table[tool],
                        key=lambda tup: datetime.strptime(tup[1], "%d %b %Y"),
                    )
                except KeyError:
                    measurement_table[tool] = [(sast_tool_result, date)]
        if not has_measurement:
            return []
        measurement_table, sorted_dates = self._format_measurements(
            measurement_table, dates
        )
        measurement_table["0::Tool"] = sorted_dates
        measurement_table["2::Ground Truth"] = [translate_bool(ground_truth)] * len(
            sorted_dates
        )
        return [
            MarkdownCollapsible(
                [MarkdownTable(measurement_table)],
                MarkdownHeading("Measurement", self.level + 1),
                is_open=True,
            )
        ]

    def _remediation(self) -> list:
        """Generates the 'remediation' section for an instance."""
        note = (
            self.current_instance_dict["remediation"]["notes"]
            if "remediation:notes" in self.current_instance_dict_keys
            else ""
        )
        note = MarkdownString(
            self._get_file_content_if_exists(note, "remediation note")
        )
        transformation = (
            self.current_instance_dict["remediation"]["transformation"]
            if "remediation:transformation" in self.current_instance_dict_keys
            else ""
        )
        transformation = MarkdownString(
            self._get_file_content_if_exists(transformation, "transformation")
        )
        modeling_rule = (
            self.current_instance_dict["remediation"]["modeling_rule"]
            if "remediation:modeling_rule" in self.current_instance_dict_keys
            else ""
        )
        modeling_rule = MarkdownString(
            self._get_file_content_if_exists(modeling_rule, "modeling rule")
        )
        if any([note, transformation, modeling_rule]):
            note = [
                note
                if note
                else MarkdownString(
                    "Can you think of a transformation, that makes this tarpit less challenging for SAST tools?"
                )
            ]
            transformation = (
                [MarkdownHeading("Transformation", self.level + 2), transformation]
                if transformation
                else []
            )
            modeling_rule = (
                [MarkdownHeading("Modeling Rule", self.level + 2), modeling_rule]
                if modeling_rule
                else []
            )
            return [
                MarkdownCollapsible(
                    note + transformation + modeling_rule,
                    MarkdownHeading("Remediation", self.level + 1),
                )
            ]
        return []

    def _get_file_content_if_exists(
        self, path_to_file: str, debug_name: str = ""
    ) -> str:
        """If the `path_to_file` is a valid filepath within the current instance, this will return the content of that file.
        Provide a `debug_name` if you want a unique logging warning.

        Args:
            path_to_file (str): path to a file within the current instance.
            debug_name (str, optional): Name, that is used in the debug output. Defaults to ''.

        Returns:
            str: content of the file or empty string.
        """
        content = path_to_file if path_to_file else ""
        if path.isfile(path.join(self.current_instance, content)):
            content = read_file(path.join(self.current_instance, content))
        if not content:
            logger.warning(
                f"{self.log_prefix}Could not find {debug_name} for instance {path.basename(self.current_instance)}"
            )
            return ""
        return content

    def _format_measurements(self, tool_measurement_dict: dict, dates: list) -> tuple:
        """Formats the measurements in the wanted table format:

        |        | Tool1  | Tool2  |
        |--------+--------+--------|
        | Date1  | yes    | no     |

        Args:
            tool_measurement_dict (dict): dict containing measurement results and date as a list of tuple for each tool.
            dates (list): a list of measurement dates.

        Returns:
            tuple(dict, list): dict of all tools and their measurement results (one column) and a list of sorted measurement dates (first column)
        """
        dates_sorted = sorted(list(set(dates)))
        formatted_measurement_table = {}
        for tool, measurements in tool_measurement_dict.items():
            formatted_measurements = []
            current_measurement = measurements.pop(0)
            for date in dates_sorted:
                if current_measurement[1] == date:
                    formatted_measurements += [current_measurement[0]]
                    if len(measurements):
                        current_measurement = measurements.pop(0)
                    else:
                        break
                else:
                    formatted_measurements += [""]
            formatted_measurement_table[tool] = formatted_measurements
        return formatted_measurement_table, dates_sorted

    def generate_md(self) -> list:
        """Entrypoint for generating Markdown for an instance,

        Returns:
            list: a list of Markdown elements following the structure in `self.instance_structure`
        """
        ret = []
        for idx, _ in enumerate(self.instances_jsons):
            self.current_instance = path.dirname(self.instances_jsons[idx])
            self.current_instance_dict = self.instance_dicts[idx]
            self.current_instance_dict_keys = get_dict_keys(self.current_instance_dict)

            instance_md_elements = []
            for f in self.instance_structure:
                instance_md_elements += f()
            if self.has_multiple_instances:
                ret += [
                    MarkdownCollapsible(
                        instance_md_elements[1:], instance_md_elements[0], idx == 0
                    )
                ]
            else:
                ret = instance_md_elements
        return ret
