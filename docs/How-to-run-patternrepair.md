# How to run: Pattern repair

## Overview

This command can be used to repair a pattern in your library. At the moment this is only supported for PHP.

## Command line

To repair a pattern use:

```text
usage: tpframework [OPTIONS] COMMAND patternrepair [-h] -l LANGUAGE (-p PATTERN_ID [PATTERN_ID ...] | --pattern-range RANGE_START-RANGE_END | -a) [--tp-lib TP_LIB_DIR]
                                                   [--output-dir OUTPUT_DIR] [--masking-file MASKING_FILE] [--measurement-results MEASUREMENT_DIR]
                                                   [--checkdiscoveryrules-results CHECKDISCOVERYRULES_FILE] [--skip-readme]

options:
  -h, --help            show this help message and exit
  -l LANGUAGE, --language LANGUAGE
                        Programming language targeted
  -p PATTERN_ID [PATTERN_ID ...], --patterns PATTERN_ID [PATTERN_ID ...]
                        Specify pattern(s) ID(s) to test for discovery
  --pattern-range RANGE_START-RANGE_END
                        Specify pattern ID range separated by`-` (ex. 10-50)
  -a, --all-patterns    Test discovery for all available patterns
  --tp-lib TP_LIB_DIR   Absolute path to alternative pattern library, default resolves to `./testability_patterns`
  --output-dir OUTPUT_DIR
                        Absolute path to the folder where outcomes (e.g., log file, export file if any) will be stored, default resolves to `./out`
  --masking-file MASKING_FILE
                        Absolute path to a json file, that contains a mapping, if the name for some measurement tools should be kept secret, default is None
  --measurement-results MEASUREMENT_DIR
                        Absolute path to the folder where measurement results are stored, default resolves to `./measurements`
  --checkdiscoveryrules-results CHECKDISCOVERYRULES_FILE
                        Absolute path to the csv file, where the results of the `checkdiscoveryrules` command are stored, default resolves to `./checkdiscoveryrules.csv`
  --skip-readme         If set, the README generation is skipped.
```

By default, the `patternrepair` will create a README file for a pattern, where an overview of the pattern is presented together with some measurement results, if available.
For the generation of the REAMDE, there are a few files mandatory:
First of all, there has to be a csv file, that contains the results of the `checkdiscoveryrules` command for the patterns, that should be repaired.
Second, the results of the `measurement` command in a directory, structured similary to the pattern library.
Additionally you can provide a masking file, that can be used to mask the names of tools used for `measurement`.
The masking file should be a JSON file of the format `{<real_tool_name>: <masked_tool_name>}`.

If `--skip-readme` is set, None of the files is required and no new README file will be generated.

## Example

`tpframework patternrepair -l php -p 1 --skip-readme`

This command will take a look at PHP pattern 1 and tries to repair it, without generating a new README file.
During that process it might provide you some feedback about files, that need manual review.
The tool checks for the following things:

- make sure, a pattern JSON file exists
- ensure all relative links are correct
- collect all instances within the pattern path (an instance is identified by a directory, that contains a JSON file in the instance format)
- make sure the pattern name is correct (therefor the pattern name is derived from the directory name)
- check the description field and warn if there is no description
- check the given tags
- validates the pattern json against the pattern json scheme
- for each instance, repairing means:
  - ensuring a instance JSON file with the required keys is available
  - ensures all relative links exist
  - check the scala rule if exists and iff necessary adjust the variable names
  - check the description and again warn if there is no description provided
  - checks that the field `expectation:expectation` is the opposite of `properties:negative_test_case`
  - validates the instance json against the instance json scheme
  - for PHP patterns:
    - generates new opcode for each php file
    - changes source line and sink line in the pattern JSON, according to the comments `// source`, `// sink` in the php file
