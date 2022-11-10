import asyncio
from argparse import ArgumentParser, Namespace
from typing import Dict

import config
from cli.add_pattern import add_pattern
from cli.discovery_pattern import run_discovery_for_all_patterns, run_discovery_for_pattern_list, manual_discovery
from cli.measure_pattern import measure_list_patterns, measure_all_pattern, get_tool_list_from_args, \
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


def main():
    parser: ArgumentParser = ArgumentParser(
        prog="tpframework",
        usage="%(prog)s [OPTIONS] COMMAND",
        description="CLI for Testability Pattern discovery and transformation",
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
        dest="patterns_discovery",
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
        dest="all_pattern_discovery",
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

    increase_testability_parser.add_argument(
        "-t", "--target",
        metavar="TARGET_DIR",
        dest="target_remediation",
        required=True,
        help="Path to target folder for increasing testability"
    )
    increase_testability_parser.add_argument(
        "-l", "--language",
        metavar="LANGUAGE",
        dest="language",
        required=True,
        help="Programming Language used in the target source code"
    )
    increase_testability_parser.add_argument(
        "-m", "--modelling-rules",
        metavar="MODELLING_RULES_FILE",
        dest="modelling_rules_file",
        required=True,
        help="Path to modelling rule file"
    )

    results_parser = subparser.add_parser("result", help="Print or export last measurement results for patterns")
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

    args: Namespace = parser.parse_args()

    match args.command:
        case "add":
            language: str = args.language.upper()
            if args.tp_lib:
                add_pattern(args.pattern_dir, language, args.measure, tools, args.json_file, args.tp_lib)
            else:
                add_pattern(args.pattern_dir, language, args.measure, tools, args.json_file)
        case "update":
            return 0
        case "measure":
            language: str = args.language.upper()
            if not args.tp_lib:
                tp_lib: str = str(config.DEFAULT_TP_LIBRARY_ROOT_DIR)
            else:
                tp_lib: str = args.tp_lib

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
            if not args.tp_lib:
                tp_lib: str = str(config.DEFAULT_TP_LIBRARY_ROOT_DIR)
            else:
                tp_lib: str = args.tp_lib

            if args.tools and len(args.tools) > 0:
                tool_parsed: list[Dict] = get_tool_list_from_args(args.tools)
            else:
                tool_parsed: list[Dict] = []

            if args.all_pattern_discovery:
                run_discovery_for_all_patterns(args.target_discovery, language, tool_parsed, tp_lib)

            if args.patterns_discovery and len(args.patterns_discovery) > 0:
                run_discovery_for_pattern_list(args.target_discovery, args.patterns_discovery,
                                               language, tool_parsed, tp_lib)
        case "inspect":
            return 0
        case "result":
            language: str = args.language.upper()
            if not args.tp_lib:
                tp_lib: str = str(config.DEFAULT_TP_LIBRARY_ROOT_DIR)
            else:
                tp_lib: str = args.tp_lib

            if args.tools and len(args.tools) > 0:
                tool_parsed: list[Dict] = get_tool_list_from_args(args.tools)
            else:
                tool_parsed: list[Dict] = tools

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


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupting...")
