import asyncio
from argparse import ArgumentParser, Namespace
from typing import Dict
from pathlib import Path
import sys

import logging
from core import loggermgr

logger = logging.getLogger(loggermgr.logger_name(__name__))

import config
from cli.add_pattern import add_pattern
from cli.discovery_pattern import run_discovery_for_all_patterns, run_discovery_for_pattern_list, manual_discovery
from cli.measure_pattern import measure_list_patterns, measure_all_pattern, \
    print_last_measurement_for_pattern_list, print_last_measurement_for_all_patterns, \
    export_to_file_last_measurement_for_all_patterns, export_to_file_last_measurement_for_pattern_list

# TODO: Dict with current supported tools to be removed
from core.discovery import discovery

tools: list[Dict] = [
    {
        "name": "codeql",
        "version": "2.9.2"
    }
]


def main(args=None):
    if not args:
        args = sys.argv[1:]
    parser: ArgumentParser = ArgumentParser(
        prog="tpframework",
        usage="%(prog)s [OPTIONS] COMMAND",
        description="CLI for the Testability Pattern framework",
        epilog="Run '%(prog)s COMMAND --help' for more information on a command."
    )

    # parser.add_argument(
    #     "--tools",
    #     metavar="tool_list",
    #     dest="tools",
    #     help="List of SAST tools to be used"
    # )

    subparser = parser.add_subparsers(title="Commands", dest="command", metavar="")

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
        help="Path to alternative lib, default is placed in `testability_patterns`"
    )
    add_pattern_parser.add_argument(
        "-m", "--measure",
        action="store_true",
        dest="measure",
        help="Measure pattern against all installed SASTs tools"
    )

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

    measure_pattern_parser = subparser.add_parser("measure", help="Run measurements for pattern(s)")
    measure_pattern_parser_pattern_selection_mode = measure_pattern_parser.add_mutually_exclusive_group(required=True)

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
        help="Specify pattern ID range separated by`-` (ex. 10-50)"
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
        "--tp-lib",
        metavar="TP_LIB_DIR",
        dest="tp_lib",
        help="Path to alternative lib, default is placed in `testability_patterns`"
    )
    measure_pattern_parser.add_argument(
        "-w", "--workers",
        metavar="NUMBER",
        dest="workers",
        type=int,
        help="Number of workers running measurements in parallel`"
    )

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
        help="Path to discovery target folder"
    )
    discovery_parser.add_argument(
        "--tools",
        metavar="TOOLS",
        dest="tools",
        nargs="+",
        type=str,
        help="List of SAST Tools for discovering pattern not supported"
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
        help="Path to alternative lib, default is placed in `testability_patterns`"
    )

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
        help="Timeout for CPG generation"
    )

    results_parser = subparser.add_parser("sastresult", help="Print or export last SAST measurement results for patterns")
    results_parser_pattern_selection_mode = results_parser.add_mutually_exclusive_group(required=True)
    results_parser_export_mode = results_parser.add_mutually_exclusive_group(required=True)
    results_parser_export_mode.add_argument(
        "--print",
        dest="print_mode",
        action="store_true",
        help="Print last measurement by tool and pattern"
    )
    results_parser_export_mode.add_argument(
        "--export",
        dest="export_mode",
        action="store_true",
        help="Print last measurement by tool and pattern"
    )
    results_parser.add_argument(
        "-t", "--tools",
        metavar="TOOLS",
        dest="tools",
        nargs="+",
        type=str,
        help="List of SAST tools to filter measurements"
    )
    results_parser.add_argument(
        "-l", "--language",
        metavar="LANGUAGE",
        dest="language",
        required=True,
        help="Programming Language used in the target source code"
    )
    results_parser_pattern_selection_mode.add_argument(
        "-p", "--patterns",
        metavar="PATTERN_ID",
        dest="patterns",
        nargs="+",
        type=int,
        help="Specify pattern(s) ID(s) to discover on the target"
    )
    results_parser_pattern_selection_mode.add_argument(
        "--pattern-range",
        metavar="RANGE_START-RANGE_END",
        dest="pattern_range",
        type=str,
        help="Specify pattern ID range separated by`-` (ex. 10-50)"
    )
    results_parser_pattern_selection_mode.add_argument(
        "-a", "--all-patterns",
        dest="all_patterns",
        action="store_true",
        help="Run discovery for all available patterns"
    )
    results_parser.add_argument(
        "--tp-lib",
        metavar="TP_LIB_DIR",
        dest="tp_lib",
        help="Path to alternative lib, default is placed in `testability_patterns`"
    )
    # Test discovery rules
    testdr_parser = subparser.add_parser("testdiscoveryrules", help="Test the discovery rules of the pattern instances on the pattern instances themselves")
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
        help="Path to alternative lib, default is placed in `testability_patterns`"
    )
    testdr_parser.add_argument(
        "-s", "--timeout",
        metavar="NUMBER",
        dest="timeout",
        type=int,
        help="Timeout for CPG generation"
    )

###########

    args: Namespace = parser.parse_args(args)

    match args.command:
        case "add":
            language: str = args.language.upper()
            tp_lib_path: str = parse_tp_lib(args.tp_lib)
            add_pattern(args.pattern_dir, language, args.measure, tools, args.json_file, tp_lib_path)
        case "update":
            logger.error("Update command not implemented yet...")
            return 0
        case "measure":
            language: str = args.language.upper()
            tp_lib_path: str = parse_tp_lib(args.tp_lib)

            pattern_id_list = parse_patterns(args.all_patterns, args.pattern_range, args.patterns, tp_lib_path, language)
            if args.all_patterns:
                asyncio.run(measure_all_pattern(language, tools, tp_lib, int(args.workers)))

            if args.pattern_range:
                pattern_range: str = args.pattern_range.split("-")
                pattern_id_list: list[int] = list(range(int(pattern_range[0]), int(pattern_range[1]) + 1))
                asyncio.run(measure_list_patterns(pattern_id_list, language, tools, tp_lib, int(args.workers)))

            if args.patterns and len(args.patterns) > 0:
                asyncio.run(measure_list_patterns(args.patterns, language, tools, tp_lib, int(args.workers)))
        case "manual-discovery":
            language: str = args.language.upper()
            timeout = 0
            if args.timeout:
                timeout = args.timeout

            manual_discovery(args.target_discovery, args.discovery_method, args.discovery_rules, language, timeout)
        case "discovery":
            language: str = args.language.upper()
            tp_lib_path: str = parse_tp_lib(args.tp_lib)
            tool_parsed: list[Dict] = parse_tool_list(args.tools)
            pattern_id_list = parse_patterns(args.all_patterns, args.pattern_range, args.patterns,
                                             tp_lib_path,
                                             language)

            if args.all_patterns:
                run_discovery_for_all_patterns(args.target_discovery, language, tool_parsed, tp_lib)

            if args.patterns and len(args.patterns) > 0:
                run_discovery_for_pattern_list(args.target_discovery, args.patterns,
                                               language, tool_parsed, tp_lib)
        case "inspect":
            return 0
        case "result":
            language: str = args.language.upper()
            tp_lib_path: str = parse_tp_lib(args.tp_lib)
            tool_parsed: list[Dict] = parse_tool_list(args.tools)

            if args.print_mode:
                if args.all_patterns:
                    print_last_measurement_for_all_patterns(tool_parsed, language, tp_lib)

                if args.pattern_range:
                    pattern_range: str = args.pattern_range.split("-")
                    pattern_id_list: list[int] = list(range(int(pattern_range[0]), int(pattern_range[1]) + 1))
                    print_last_measurement_for_pattern_list(tool_parsed, language, pattern_id_list, tp_lib)

                if args.patterns and len(args.patterns) > 0:
                    print_last_measurement_for_pattern_list(tool_parsed, language, args.patterns, tp_lib)

            if args.export_mode:
                if args.all_patterns:
                    export_to_file_last_measurement_for_all_patterns(tool_parsed, language, tp_lib)

                if args.pattern_range:
                    pattern_range: str = args.pattern_range.split("-")
                    pattern_id_list: list[int] = list(range(int(pattern_range[0]), int(pattern_range[1]) + 1))
                    export_to_file_last_measurement_for_pattern_list(
                        tool_parsed, language, pattern_id_list, tp_lib)

                if args.patterns and len(args.patterns) > 0:
                    export_to_file_last_measurement_for_pattern_list(tool_parsed, language, args.patterns, tp_lib)

        case "testdiscoveryrules":
            language: str = args.language.upper()
            tp_lib_path: str = parse_tp_lib(args.tp_lib)
            if args.print_mode:
                if args.all_patterns:
                    print_last_measurement_for_all_patterns(tool_parsed, language, tp_lib)

                if args.pattern_range:
                    pattern_range: str = args.pattern_range.split("-")
                    pattern_id_list: list[int] = list(range(int(pattern_range[0]), int(pattern_range[1]) + 1))
                    print_last_measurement_for_pattern_list(tool_parsed, language, pattern_id_list, tp_lib)

                if args.patterns and len(args.patterns) > 0:
                    print_last_measurement_for_pattern_list(tool_parsed, language, args.patterns, tp_lib)

            if args.export_mode:
                if args.all_patterns:
                    export_to_file_last_measurement_for_all_patterns(tool_parsed, language, tp_lib)

                if args.pattern_range:
                    pattern_range: str = args.pattern_range.split("-")
                    pattern_id_list: list[int] = list(range(int(pattern_range[0]), int(pattern_range[1]) + 1))
                    export_to_file_last_measurement_for_pattern_list(
                        tool_parsed, language, pattern_id_list, tp_lib)

                if args.patterns and len(args.patterns) > 0:
                    export_to_file_last_measurement_for_pattern_list(tool_parsed, language, args.patterns, tp_lib)


def parse_tp_lib(tp_lib: str):
    if not tp_lib:
        tp_lib: str = str(config.DEFAULT_TP_LIBRARY_ROOT_DIR)
    tp_lib_path: Path = Path(tp_lib).resolve()
    if not tp_lib_path.is_dir():
        msg = f"Specified `{tp_lib}` is not a folder or does not exists"
        logger.error(msg)
        print(msg, file=sys.stderr)
        raise FileNotFoundError
    return tp_lib_path


def parse_tool_list(tools: list[str]):
    if tools and len(tools) > 0:
        return list(map(lambda t: {"name": t.split(":")[0], "version": t.split(":")[1]}, tools))
    return []


def parse_patterns(all_patterns: bool, pattern_range: str, patterns, tp_lib_path: Path, language: str): # TODO: add missing types
    assert sum(bool(e) for e in [all_patterns, pattern_range, patterns]) == 1 # these elements are in mutual exclusion
    if all_patterns:
        lang_tp_lib_path: Path = tp_lib_path / language
        if not lang_tp_lib_path.is_dir():
            msg = f"Specified language folder`{lang_tp_lib_path}` does not exists"
            logger.error(msg)
            print(msg, file=sys.stderr)
            raise FileNotFoundError
        id_list: list[int] = list(map(lambda d: int(d.name.split("_")[0]), list(lang_tp_lib_path.iterdir())))
        return id_list
    if pattern_range:
        spattern_range: str = pattern_range.split("-")
        pattern_id_list: list[int] = list(range(int(spattern_range[0]), int(spattern_range[1]) + 1))
        return pattern_id_list
    if patterns and len(patterns) > 0:
        return patterns


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupting...")
