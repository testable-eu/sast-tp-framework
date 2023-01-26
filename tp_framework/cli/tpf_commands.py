from abc import ABC, abstractmethod
import asyncio
from pathlib import Path
from typing import Dict

import config
from cli import interface
from core import utils

from core.exceptions import InvalidSastTools
from core.errors import invalidSastTools

class Command(ABC):

    @abstractmethod
    def add_command_subparser(self, subparser):
        pass

    @abstractmethod
    def execute_command(self, args):
        pass


class AddPattern(Command):

    # overriding abstract method
    def add_command_subparser(self, subparser):
        add_pattern_parser = subparser.add_parser("add", help="Add pattern to the library")
        add_pattern_parser.add_argument(
            "-p", "--pattern-dir",
            metavar="PATTERN_DIR",
            dest="pattern_dir",
            required=True,
            help="Path to pattern directory"
        )
        add_pattern_parser.add_argument(
            "-l", "--language",
            metavar="LANGUAGE",
            dest="language",
            required=True,
            help="Programming Language used in the pattern"
        )
        add_pattern_parser.add_argument(
            "-j", "--json",
            metavar="JSON_FILE",
            dest="json_file",
            help="Path to JSON file containing pattern's metadata"
        )
        add_pattern_parser.add_argument(
            "--tp-lib",
            metavar="TP_LIB_DIR",
            dest="tp_lib",
            help=f"Absolute path to alternative pattern library, default resolves to `./{config.TP_LIB_REL_DIR}`"
        )
        add_pattern_parser.add_argument(
            "-m", "--measure",
            action="store_true",
            default=False,
            dest="measure",
            help="Measure pattern against SASTs tools. (False by default)"
        )
        add_pattern_parser.add_argument(
            "--tools",
            metavar="TOOLS",
            dest="tools",
            nargs="+",
            type=str,
            help="List of SAST Tools (default in `config.py`) that will be used for measurement, if --measure is specified."
        )

    # overriding abstract method
    def execute_command(self, args):
        language: str = args.language.upper()
        tp_lib_path: str = parse_tp_lib(args.tp_lib)
        tool_parsed: list[Dict] = parse_tool_list(args.tools)
        interface.add_pattern(args.pattern_dir, language, args.measure, tool_parsed, args.json_file, tp_lib_path)


class UpdatePattern(Command):

    # overriding abstract method
    def add_command_subparser(self, subparser):
        update_pattern_parser = subparser.add_parser("update", help="Update pattern already present in the library")
        update_pattern_parser.add_argument(
            "-p", "--pattern-dir",
            metavar="PATTERN_DIR",
            dest="pattern_dir",
            required=True,
            help="Path to updated pattern directory"
        )
        update_pattern_parser.add_argument(
            "-j", "--json",
            metavar="JSON_FILE",
            dest="json_file",
            help="Path to JSON file containing updated pattern's metadata"
        )

    # overriding abstract method
    def execute_command(self, args):
        print("Update command not implemented yet...")
        return 0


class MeasurePatterns(Command):

    # overriding abstract method
    def add_command_subparser(self, subparser):
        measure_pattern_parser = subparser.add_parser("measure", help="Run measurements for pattern(s)")
        measure_pattern_parser_pattern_selection_mode = measure_pattern_parser.add_mutually_exclusive_group(
            required=True)
        measure_pattern_parser_pattern_selection_mode.add_argument(
            "-p", "--patterns",
            metavar="PATTERN_ID",
            dest="patterns",
            nargs="+",
            type=int,
            help="Specify pattern(s) ID(s) to measures"
        )
        measure_pattern_parser_pattern_selection_mode.add_argument(
            "--pattern-range",
            metavar="RANGE_START-RANGE_END",
            dest="pattern_range",
            type=str,
            help="Specify pattern ID range separated by `-` (e.g., 10-50)"
        )
        measure_pattern_parser_pattern_selection_mode.add_argument(
            "-a", "--all-patterns",
            dest="all_patterns",
            action="store_true",
            help="Specify to run measurement on all patterns"
        )
        measure_pattern_parser.add_argument(
            "-l", "--language",
            metavar="LANGUAGE",
            dest="language",
            required=True,
            help="Programming Language used in the pattern"
        )
        measure_pattern_parser.add_argument(
            "--tools",
            metavar="TOOLS",
            dest="tools",
            nargs="+",
            type=str,
            help="List of SAST Tools (default in `config.py`) that will be run, if they support the language"
        )
        measure_pattern_parser.add_argument(
            "--tp-lib",
            metavar="TP_LIB_DIR",
            dest="tp_lib",
            help=f"Absolute path to alternative pattern library, default resolves to `./{config.TP_LIB_REL_DIR}`"
        )
        measure_pattern_parser.add_argument(
            "-w", "--workers",
            metavar="NUMBER",
            default=config.WORKERS,
            dest="workers",
            type=int,
            help=f"Number of workers running measurements in parallel ({config.WORKERS} by default)"
        )


    # overriding abstract method
    def execute_command(self, args):
        language: str = args.language.upper()
        tp_lib_path: str = parse_tp_lib(args.tp_lib)
        l_pattern_id = parse_patterns(args.all_patterns, args.pattern_range, args.patterns, tp_lib_path, language)
        tool_parsed: list[Dict] = parse_tool_list(args.tools)
        asyncio.run(interface.measure_list_patterns(l_pattern_id, language, tools=tool_parsed, tp_lib_path=tp_lib_path, workers = int(args.workers)))


class DiscoveryPatterns(Command):

    # overriding abstract method
    def add_command_subparser(self, subparser):
        discovery_parser = subparser.add_parser("discovery",
                                                help="Run pattern discovery on a folder containing the source code of an application")
        discovery_parser_pattern_selection_mode = discovery_parser.add_mutually_exclusive_group(required=True)
        discovery_parser_pattern_selection_mode.add_argument(
            "-p", "--patterns",
            metavar="PATTERN_ID",
            dest="patterns",
            nargs="+",
            type=int,
            help="Specify pattern(s) ID(s) to discover on the target"
        )
        discovery_parser_pattern_selection_mode.add_argument(
            "--pattern-range",
            metavar="RANGE_START-RANGE_END",
            dest="pattern_range",
            type=str,
            help="Specify pattern ID range separated by`-` (ex. 10-50)"
        )
        discovery_parser_pattern_selection_mode.add_argument(
            "-a", "--all-patterns",
            dest="all_patterns",
            action="store_true",
            help="Run discovery for all available patterns"
        )
        discovery_parser.add_argument(
            "-t", "--target",
            metavar="TARGET_DIR",
            dest="target_discovery",
            required=True,
            help="Path to discovery target folder"
        )
        discovery_parser.add_argument(
            "--tools",
            metavar="TOOLS",
            dest="tools",
            nargs="+",
            type=str,
            help="List of SAST Tools (default in `config.py`) filtering on pattern discovery. Only the pattern instances not supported by at least one tool will be run for discovery."
        )
        discovery_parser.add_argument(
            "-i", "--ignore-measurements",
            action="store_true",
            default=False,
            dest="ignore",
            help="Ignore measurement results from SAST tools and just try to discover all the specified patterns. (False by default)."
        )
        discovery_parser.add_argument(
            "-l", "--language",
            metavar="LANGUAGE",
            dest="language",
            required=True,
            help="Programming Language used in the target source code"
        )
        discovery_parser.add_argument(
            "--tp-lib",
            metavar="TP_LIB_DIR",
            dest="tp_lib",
            help=f"Absolute path to alternative pattern library, default resolves to `./{config.TP_LIB_REL_DIR}`"
        )
        discovery_parser.add_argument(
            "--output-dir",
            metavar="OUTPUT_DIR",
            dest="output_dir",
            help=f"Absolute path to the folder where outcomes will be stored, default resolves to `./{config.RESULT_REL_DIR}`"
        )

    # overriding abstract method
    def execute_command(self, args):
        language: str = args.language.upper()
        tp_lib_path: str = parse_tp_lib(args.tp_lib)
        target_dir = Path(args.target_discovery)
        utils.check_target_dir(target_dir)
        output_dir: str = parse_output_dir(args.output_dir)
        tool_parsed: list[Dict] = parse_tool_list(args.tools)
        l_pattern_id = parse_patterns(args.all_patterns, args.pattern_range, args.patterns,
                                      tp_lib_path,
                                      language)
        try:
            interface.run_discovery_for_pattern_list(target_dir, l_pattern_id, language, tool_parsed, tp_lib_path,
                                                     output_dir=output_dir, ignore=args.ignore)
        except InvalidSastTools:
            print(invalidSastTools())
            exit(1)


class ManualDiscovery(Command):

    # overriding abstract method
    def add_command_subparser(self, subparser):
        manual_discovery_parser = subparser.add_parser("manual-discovery",
                                                       help="Run discovery on a folder containing the source code of an application given a discovery method and a set of discovery rules")
        manual_discovery_parser.add_argument(
            "-t", "--target",
            metavar="TARGET_DIR",
            dest="target_discovery",
            required=True,
            help="Path to discovery target folder"
        )
        manual_discovery_parser.add_argument(
            "-l", "--language",
            metavar="LANGUAGE",
            dest="language",
            required=True,
            help="Programming Language used in the target source code"
        )
        manual_discovery_parser.add_argument(
            "-m", "--method",
            metavar="METHOD",
            dest="discovery_method",
            required=True,
            help="Discovery method to perform discovery operation"
        )
        manual_discovery_parser.add_argument(
            "-r", "--rules",
            metavar="RULES_PATH",
            dest="discovery_rules",
            nargs="+",
            type=str,
            required=True,
            help="Path to file(s) or directory containing a set of discovery rules"
        )
        manual_discovery_parser.add_argument(
            "-s", "--timeout",
            metavar="NUMBER",
            dest="timeout",
            type=int,
            help="Timeout for single discovery operation. No timeout by default"
        )
        manual_discovery_parser.add_argument(
            "--output-dir",
            metavar="OUTPUT_DIR",
            dest="output_dir",
            help=f"Absolute path to the folder where outcomes will be stored, default resolves to `./{config.RESULT_REL_DIR}`"
        )


    # overriding abstract method
    def execute_command(self, args):
        language: str = args.language.upper()
        target_dir = Path(args.target_discovery)
        utils.check_target_dir(target_dir)
        output_dir: str = parse_output_dir(args.output_dir)
        timeout = 0
        if args.timeout:
            timeout = args.timeout

        interface.manual_discovery(target_dir, args.discovery_method, args.discovery_rules, language, timeout, output_dir=output_dir)


class Report(Command):

    # overriding abstract method
    def add_command_subparser(self, subparser):
        report_parser = subparser.add_parser("sastreport",
                                              help="Report about SAST measurement results for patterns")
        report_parser_pattern_selection_mode = report_parser.add_mutually_exclusive_group(required=True)
        report_parser_export_mode = report_parser.add_mutually_exclusive_group(required=True)
        report_parser_export_mode.add_argument(
            "--print",
            dest="print_mode",
            action="store_true",
            help="Print measurements on stdout."
        )
        report_parser_export_mode.add_argument(
            "--export",
            metavar="EXPORTFILE",
            dest="export",
            help="Export measurements to the specified csv file."
        )
        report_parser.add_argument(
            "-t", "--tools",
            metavar="TOOLS",
            dest="tools",
            nargs="+",
            type=str,
            help="List of SAST tools (default in `config.py`) for which the measurements will be reported in the results."
        )
        report_parser.add_argument(
            "-l", "--language",
            metavar="LANGUAGE",
            dest="language",
            required=True,
            help="Programming Language used in the target source code"
        )
        report_parser_pattern_selection_mode.add_argument(
            "-p", "--patterns",
            metavar="PATTERN_ID",
            dest="patterns",
            nargs="+",
            type=int,
            help="Specify pattern(s) ID(s) to report about"
        )
        report_parser_pattern_selection_mode.add_argument(
            "--pattern-range",
            metavar="RANGE_START-RANGE_END",
            dest="pattern_range",
            type=str,
            help="Specify pattern ID range separated by`-` (ex. 10-50)"
        )
        report_parser_pattern_selection_mode.add_argument(
            "-a", "--all-patterns",
            dest="all_patterns",
            action="store_true",
            help="Report about all available patterns"
        )
        report_parser.add_argument(
            "--tp-lib",
            metavar="TP_LIB_DIR",
            dest="tp_lib",
            help=f"Absolute path to alternative pattern library, default resolves to `./{config.TP_LIB_REL_DIR}`"
        )
        report_parser.add_argument(
            "--output-dir",
            metavar="OUTPUT_DIR",
            dest="output_dir",
            help=f"Absolute path to the folder where outcomes (e.g., log file, export file if any) will be stored, default resolves to `./{config.RESULT_REL_DIR}`"
        )
        # report_parser.add_argument(
        #     "--only-last-measurement",
        #     action="store_true",
        #     default=True,
        #     dest="only_last_measurement",
        #     help="Report only about the last measurements result of each pattern instance. (True by default)"
        # )


    # overriding abstract method
    def execute_command(self, args):
        language: str = args.language.upper()
        tp_lib_path: str = parse_tp_lib(args.tp_lib)
        tool_parsed: list[Dict] = parse_tool_list(args.tools)
        l_pattern_id = parse_patterns(args.all_patterns, args.pattern_range, args.patterns,
                                      tp_lib_path,
                                      language)
        output_dir: str = parse_output_dir(args.output_dir)
        only_last_measurement: bool = True # TODO: adjust when --only-last-measurement=False will be implemented
        if args.export:
            interface.report_sast_measurement_for_pattern_list(
                tool_parsed, language, l_pattern_id, tp_lib_path,
                export_file=args.export, output_dir=output_dir, only_last_measurement=only_last_measurement)
            # interface.export_to_file_last_measurement_for_pattern_list(tool_parsed, language, l_pattern_id, tp_lib_path)
        else:
            interface.report_sast_measurement_for_pattern_list(
                tool_parsed, language, l_pattern_id, tp_lib_path,
                output_dir=output_dir, only_last_measurement=only_last_measurement)




class TestDiscoveryRules(Command):

    # overriding abstract method
    def add_command_subparser(self, subparser):
        testdr_parser = subparser.add_parser("testdiscoveryrules",
                                             help="Test the discovery rules of the pattern instances on the pattern instances themselves")
        testdr_parser_pattern_selection_mode = testdr_parser.add_mutually_exclusive_group(required=True)
        testdr_parser_export_mode = testdr_parser.add_mutually_exclusive_group(required=True)
        testdr_parser_export_mode.add_argument(
            "--print",
            dest="print_mode",
            action="store_true",
            help="Print test results"
        )
        testdr_parser_export_mode.add_argument(
            "--export",
            dest="export_mode",
            action="store_true",
            help="Export test results"
        )
        testdr_parser.add_argument(
            "-l", "--language",
            metavar="LANGUAGE",
            dest="language",
            required=True,
            help="Programming Language used in the target source code"
        )
        testdr_parser_pattern_selection_mode.add_argument(
            "-p", "--patterns",
            metavar="PATTERN_ID",
            dest="patterns",
            nargs="+",
            type=int,
            help="Specify pattern(s) ID(s) to discover on the target"
        )
        testdr_parser_pattern_selection_mode.add_argument(
            "--pattern-range",
            metavar="RANGE_START-RANGE_END",
            dest="pattern_range",
            type=str,
            help="Specify pattern ID range separated by`-` (ex. 10-50)"
        )
        testdr_parser_pattern_selection_mode.add_argument(
            "-a", "--all-patterns",
            dest="all_patterns",
            action="store_true",
            help="Run discovery for all available patterns"
        )
        testdr_parser.add_argument(
            "--tp-lib",
            metavar="TP_LIB_DIR",
            dest="tp_lib",
            help=f"Absolute path to alternative pattern library, default resolves to `./{config.TP_LIB_REL_DIR}`"
        )
        testdr_parser.add_argument(
            "-s", "--timeout",
            metavar="NUMBER",
            dest="timeout",
            type=int,
            help="Timeout for CPG generation"
        )

    # overriding abstract method
    def execute_command(self, args):
        language: str = args.language.upper()
        tp_lib_path: str = parse_tp_lib(args.tp_lib)
        if args.print_mode:
            if args.all_patterns:
                interface.print_last_measurement_for_all_patterns(tool_parsed, language, tp_lib)

            if args.pattern_range:
                pattern_range: str = args.pattern_range.split("-")
                l_pattern_id: list[int] = list(range(int(pattern_range[0]), int(pattern_range[1]) + 1))
                interface.report_sast_measurement_for_pattern_list(tool_parsed, language, l_pattern_id, tp_lib)

            if args.patterns and len(args.patterns) > 0:
                interface.report_sast_measurement_for_pattern_list(tool_parsed, language, args.patterns, tp_lib)

        if args.export_mode:
            if args.all_patterns:
                interface.export_to_file_last_measurement_for_all_patterns(tool_parsed, language, tp_lib)

            if args.pattern_range:
                pattern_range: str = args.pattern_range.split("-")
                l_pattern_id: list[int] = list(range(int(pattern_range[0]), int(pattern_range[1]) + 1))
                interface.export_to_file_last_measurement_for_pattern_list(
                    tool_parsed, language, l_pattern_id, tp_lib)

            if args.patterns and len(args.patterns) > 0:
                interface.export_to_file_last_measurement_for_pattern_list(tool_parsed, language, args.patterns, tp_lib)


# class Template(Command):
#
#     # overriding abstract method
#     def add_command_subparser(self, subparser):
#         pass
#     # overriding abstract method
#     def execute_command(self, args):
#         pass


# Parser utils

def parse_tp_lib(tp_lib: str):
    if not tp_lib:
        tp_lib: str = str(config.DEFAULT_TP_LIBRARY_ROOT_DIR)
    try:
        tp_lib_path: Path = Path(tp_lib).resolve()
        utils.check_tp_lib(tp_lib_path)
        return tp_lib_path
    except Exception as e:
        print(f"Testability pattern library is wrong or not found: {tp_lib}")
        exit(1)


def parse_output_dir(output_dir: str):
    if not output_dir:
        output_dir: str = str(config.RESULT_DIR)
    try:
        output_dir_path: Path = Path(output_dir).resolve()
        return output_dir_path
    except Exception as e:
        print(f"Output directory is wrong: {output_dir}")
        exit(1)


def parse_tool_list(tools: list[str]):
    if not tools:
        return config.SAST_TOOLS_ENABLED
    else:
        try:
            return list(map(lambda t: {"name": t.split(":")[0], "version": t.split(":")[1]}, tools))
        except Exception as e:
            print("Invalid list of SAST Tools. The format shall be a list of pairs `name:version`. E.g., `codeql:2.9.2`.")
            exit(1)


def parse_patterns(all_patterns: bool, pattern_range: str, patterns, tp_lib_path: Path, language: str):
    try:
        assert sum(bool(e) for e in [all_patterns, pattern_range, patterns]) == 1 # these elements are in mutual exclusion
    except Exception as e:
        print("The following parameters are in mutual exclusion: `--all-patterns`, `--pattern-range`, and `--patterns`")
        exit(1)
    if all_patterns:
        lang_tp_lib_path: Path = tp_lib_path / language
        utils.check_lang_tp_lib_path(lang_tp_lib_path)
        try:
            id_list: list[int] = list(map(lambda d: utils.get_id_from_name(d.name), list(lang_tp_lib_path.iterdir())))
            return id_list
        except Exception as e:
            print("Some patterns could not be properly fetched from the pattern library.")
            exit(1)
    if pattern_range:
        try:
            spattern_range: str = pattern_range.split("-")
            pattern_id_list: list[int] = list(range(int(spattern_range[0]), int(spattern_range[1]) + 1))
            return pattern_id_list
        except Exception as e:
            print("Pattern range could not be properly parsed. ")
            exit(1)
    if patterns and len(patterns) > 0:
        return patterns