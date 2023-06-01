from pathlib import Path

from core import utils
from core.pattern import get_pattern_path_by_pattern_id
from pattern_repair.pattern_repair import PatternRepair


def repair_patterns(
    language: str,
    pattern_ids: list[int],
    include_README: bool,
    checkdiscoveryrule_results: Path,
    measurement_results: Path,
    masking_file: Path,
    tp_lib_path: Path,
    output_dir: Path,
) -> None:
    """Interface, that starts a pattern repair

    Args:
        language (str): language of the targetted patterns
        pattern_ids (list[int]): list of pattern ids
        checkdiscoveryrule_results (Path): results of `checkdiscoveryrules` run with tp-framework, for all patterns to repair
        measurement_results (Path): results of `measure` run with tp-framework, for all patterns to repair
        masking_file (Path): file that can be used to Mask the name of tools, if they should be kept secret
        tp_lib_path (Path): Path to tesability pattern library
        output_dir (Path): Output dir for any written data
    """
    print("Pattern Repair started...")
    should_include_readme = not include_README
    utils.check_tp_lib(tp_lib_path)
    if should_include_readme:
        utils.check_file_exist(checkdiscoveryrule_results)
        utils.check_file_exist(masking_file, ".json") if masking_file else None
        utils.check_measurement_results_exist(measurement_results)
    output_dir.mkdir(exist_ok=True, parents=True)
    utils.add_loggers(output_dir)

    for pattern_id in pattern_ids:
        pattern_path = get_pattern_path_by_pattern_id(language, pattern_id, tp_lib_path)
        PatternRepair(
            pattern_path,
            language,
            tp_lib_path,
            checkdiscoveryrule_results,
            masking_file,
            measurement_results,
        ).repair(should_include_readme)
