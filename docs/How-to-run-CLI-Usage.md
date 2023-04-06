# How to run: CLI Usage

## CLI general description

TP Framework can be used through a CLI:

```bash
tpframework [OPTIONS] COMMAND
```

To see the list for both mandatory and optional arguments, for each specific `COMMAND` type:

```bash
tpframework COMMAND --help
```

The following main commands are currently implemented:

- [`add`](./How-to-run-add-pattern.md): add a pattern
- [`measure`](./How-to-run-Measure-SAST-tools-over-patterns.md): measure SAST tools against patterns
- discovery: discover patterns in project source code
  - [`discovery`](./How-to-run-discover-measured-patterns.md): discover measured patterns within a project source code
  - [`manual-discovery`](./How-to-run-manual-discovery.md): execute discovery rules (normally associated to patterns) within a project source code
- reporting: create reports about SAST measurement and/or pattern discovery (**TODO**)

The following are under-investigation:

- `update`: update a pattern (*to be implemented*)
- `scan`: scan a project source code (*to be implemented*)
- `remediation`: remediate a pattern via code transformations, SAST custom rules, ... (*to be implemented*)
