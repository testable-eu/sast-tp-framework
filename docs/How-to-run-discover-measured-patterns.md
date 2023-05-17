# How to run: Discover measured patterns

## Overview

This commands allows to discover pattern instances over a targeted source code. This requires the pattern instances intended to be discovered to be associated with discovery rules. This commands come in two variants:
- discovery _considering_ last SAST measurements: consider only the pattern instances not supported by any of the SAST tools specified. This requires the SAST measurements for those instances to have been run beforehand. 
- discovery _ignoring_ SAST measurements: consider all the specified pattern instances regardless of the SAST measurements (if any already done)  

The first variant is particularly useful when you have a precise arsenal of SAST tools and you only want to search for the patterns that are problematic to your arsenal. 

## Command line

To discover patterns within a project source code run:

```bash
tpframework discovery --help
usage: tpframework [OPTIONS] COMMAND discovery [-h] (-p PATTERN_ID [PATTERN_ID ...] | --pattern-range RANGE_START-RANGE_END | -a) -t TARGET_DIR [-i] [--tools TOOLS [TOOLS ...]]
                                               -l LANGUAGE [--tp-lib TP_LIB_DIR] [--output-dir OUTPUT_DIR]

options:
  -h, --help            show this help message and exit
  -p PATTERN_ID [PATTERN_ID ...], --patterns PATTERN_ID [PATTERN_ID ...]
                        Specify pattern(s) ID(s) to discover on the target
  --pattern-range RANGE_START-RANGE_END
                        Specify pattern ID range separated by`-` (ex. 10-50)
  -a, --all-patterns    Run discovery for all available patterns
  -t TARGET_DIR, --target TARGET_DIR
                        Path to discovery target folder
  -i, --ignore-measurements
                        Ignore measurement results from SAST tools and just try to discover all the specified patterns. (False by default).
  --tools TOOLS [TOOLS ...]
                        List of SAST Tools (default in `config.py`) filtering on pattern discovery. Only the pattern instances not supported by at least one tool will be run for
                        discovery. An empty list is only accepted if `--ignore-measurement` is provided.
  -l LANGUAGE, --language LANGUAGE
                        Programming Language used in the target source code
  --tp-lib TP_LIB_DIR   Absolute path to alternative pattern library, default resolves to `./testability_patterns`
  --output-dir OUTPUT_DIR
                        Absolute path to the folder where outcomes will be stored, default resolves to `./out`
```
**Important**: In the past this command worked only for those patterns that have been already measured. This constraint have been relaxed. 

## Example

### Example 1
Here a simple example that will run discovery for patterns 1 and 2 of the PHP catalog within the project `myproject`, considering the SAST measurements:
`tpframework discovery -p 1 2 -l PHP -t /myproject --tools PHPSASTTool1:v1.2.3 PHPSASTTool2:v4.5.6`

Notice that it will run only the discovery rules associated to those instances of PHP patterns 1 and 2 for which either `PHPSASTTool1` or `PHPSASTTool2`  failed.   

### Example 2
Here a simple example that will run discovery for patterns 1 and 2 of the PHP catalog within the project `myproject`, regardless of the SAST measurements:
`tpframework discovery -p 1 2 -l PHP -t /myproject --ignore-measurements`

## Required fields in instance `json` metadata

The explanation for the instance `json` metadata can be found [here](https://github.com/testable-eu/sast-testability-patterns/blob/master/docs/testability-patterns-structure.md)