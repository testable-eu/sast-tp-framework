from argparse import ArgumentParser, Namespace
import sys

from cli import tpf_commands

def main(args=None):
    if not args:
        args = sys.argv[1:]
    parser: ArgumentParser = ArgumentParser(
        prog="tpframework",
        usage="%(prog)s [OPTIONS] COMMAND",
        description="CLI for the Testability Pattern framework",
        epilog="Run '%(prog)s COMMAND --help' for more information on a command."
    )
    # Commands: init
    add_pattern_cmd = tpf_commands.AddPattern()
    update_pattern_cmd = tpf_commands.UpdatePattern()
    measure_pattern_cmd = tpf_commands.MeasurePatterns()
    discovery_pattern_cmd = tpf_commands.DiscoveryPatterns()
    manual_discovery_cmd = tpf_commands.ManualDiscovery()
    sastreport_cmd = tpf_commands.SASTReport()
    check_discovery_rules_cmd = tpf_commands.CheckDiscoveryRules()
    # Sub-parsers
    subparser = parser.add_subparsers(title="Commands", dest="command", metavar="")
    add_pattern_cmd.add_command_subparser(subparser)
    update_pattern_cmd.add_command_subparser(subparser) # TODO: not-implemented yet
    measure_pattern_cmd.add_command_subparser(subparser)
    discovery_pattern_cmd.add_command_subparser(subparser)
    manual_discovery_cmd.add_command_subparser(subparser)
    sastreport_cmd.add_command_subparser(subparser)
    check_discovery_rules_cmd.add_command_subparser(subparser) # TODO: in-progress, not tested

    # Parsing
    args: Namespace = parser.parse_args(args)

    match args.command:
        case "add":
            add_pattern_cmd.execute_command(args)
        case "update":
            update_pattern_cmd.execute_command(args)
        case "measure":
            measure_pattern_cmd.execute_command(args)
        case "manual-discovery":
            manual_discovery_cmd.execute_command(args)
        case "discovery":
            discovery_pattern_cmd.execute_command(args)
        case "inspect":
            return 0
        case "sastreport":
            sastreport_cmd.execute_command(args)
        case "checkdiscoveryrules":
            check_discovery_rules_cmd.execute_command(args)
        case other:
            print("Command not valid...")
            exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupting...")
    except Exception:
        exit(1)