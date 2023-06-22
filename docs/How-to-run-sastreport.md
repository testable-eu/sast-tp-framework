# How to run: Report about latest measurements of SAST tools over patterns

## Overview

This command aggregates in a single report the measurements obtained by running the SAST tools against the patterns in the catalogs (cf. [`measure`](./How-to-run-Measure-SAST-tools-over-patterns.md)). 
The goal is to have a precise overview of the SAST tools accuracy against patterns. For instance, this enables to see how a new version of SAST tool improves over the previous one (provided that SAST measurements for both tools have been run).

## Command line

To report about SAST measurements run:

```bash
tpframework [OPTIONS] COMMAND sastreport [-h] (--print | --export EXPORTFILE) [-t TOOLS [TOOLS ...]] -l LANGUAGE (-p PATTERN_ID [PATTERN_ID ...] | --pattern-range RANGE_START-RANGE_END | -a) [--tp-lib TP_LIB_DIR] [--output-dir OUTPUT_DIR]

options:
  -h, --help            show this help message and exit
  --print               Print measurements on stdout.
  --export EXPORTFILE   Export measurements to the specified csv file.
  -t TOOLS [TOOLS ...], --tools TOOLS [TOOLS ...]
                        List of SAST tools (default in `config.py`) for which the measurements will be reported in the results.
  -l LANGUAGE, --language LANGUAGE
                        Programming Language used in the target source code
  -p PATTERN_ID [PATTERN_ID ...], --patterns PATTERN_ID [PATTERN_ID ...]
                        Specify pattern(s) ID(s) to report about
  --pattern-range RANGE_START-RANGE_END
                        Specify pattern ID range separated by`-` (ex. 10-50)
  -a, --all-patterns    Report about all available patterns
  --tp-lib TP_LIB_DIR   Absolute path to alternative pattern library, default resolves to `./testability_patterns`
  --output-dir OUTPUT_DIR
                        Absolute path to the folder where outcomes (e.g., log file, export file if any) will be stored, default resolves to `./out`
```

You have to at least provide the report output method (`--print` or `--export EXPORTFILE`), the language (`LANGUAGE`) and some patterns (e.g., via pattern ids or id ranges) for which the measurement report will be created.
Instead of specifying certain patterns, you can use `-a` to target all patterns in `LANGUAGE`. 

*Optional*: By default the framework will use `./testability_pattern` folder as root for TP Catalog, but you can specify a different one by adding the *optional* argument `--tp-lib TP_LIB_DIR` to your command.

## Example

Here a simple example that will report about SAST measureemnt of patterns 1, 2, 4 and 7 from the PHP catalog:

```bash
tpframework sastreport -l PHP -p 1 2 4 7 --print
```

## Required fields in instance `json` metadata

The explanation for the instance `json` metadata can be found [here](https://github.com/testable-eu/sast-testability-patterns/blob/master/docs/testability-patterns-structure.md)
TODO: write here which json fields are required so that the framework can implement measure
