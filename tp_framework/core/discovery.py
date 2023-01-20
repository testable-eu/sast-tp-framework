import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime

import logging
from core import loggermgr

logger = logging.getLogger(loggermgr.logger_name(__name__))

import config
from core import utils, measurement
from core.exceptions import DiscoveryMethodNotSupported, MeasurementNotFound, CPGGenerationError, \
    CPGLanguageNotSupported, JoernQueryError
from core.measurement import Measurement


mand_finding_joern_keys = ["filename", "methodFullName", "lineNumber"]


def generate_cpg(rel_src_dir_path: Path, language: str, build_name: str, output_dir: Path,
                 timeout_sec: int = 0) -> Path:
    try:
        language_cpg_conf: Dict = utils.load_yaml(config.JOERN_CPG_GEN_CONFIG_FILE)["cpg_gen"][language.lower()]
    except KeyError as e:
        ee = CPGLanguageNotSupported(e)
        logger.exception(ee)
        raise ee

    gen_cpg_with_params_cmd: str = language_cpg_conf['command']
    if not output_dir:
        output_dir: Path = config.RESULT_DIR / "cpg_tmp"
    output_dir.mkdir(parents=True, exist_ok=True)
    binary_out: Path = output_dir / f"cpg_{build_name}.bin"

    src_dir: Path = config.ROOT_DIR / rel_src_dir_path
    gen_cpg_with_params_cmd = gen_cpg_with_params_cmd.replace("$SRC_DIR", str(src_dir.resolve()))
    gen_cpg_with_params_cmd = gen_cpg_with_params_cmd.replace("$BINARY_OUT", str(binary_out))

    if timeout_sec > 0:
        gen_cpg_with_params_cmd = f"timeout {timeout_sec} {gen_cpg_with_params_cmd}"

    os.chdir(config.ROOT_DIR / language_cpg_conf['installation_dir'])
    try:
        cpg_gen_output = run_generate_cpg_cmd(gen_cpg_with_params_cmd)
    except Exception:
        logger.debug("CPG generation failed while running the os command")
        rs = CPGGenerationError()
        logger.exception(rs)
        raise rs
    try:
        joern_scala_query_for_test_cmd = f"joern --script {Path(__file__).parent.resolve()}/cpgTest.sc --params name={binary_out}"
        cpg_gen_test_result: str = run_joern_scala_query_for_test(joern_scala_query_for_test_cmd)
        if "Error in CPG generation" in cpg_gen_test_result:
            logger.debug("CPG generation failed: reported by Joern, CPG generation command was successful")
            rs = CPGGenerationError()
            logger.exception(rs)
            raise rs
    except:
        logger.debug("CPG generation failed: exception while loading the CPG in Joern, CPG generation command was successful")
        rs = CPGGenerationError()
        logger.exception(rs)
        raise rs
    os.chdir(config.ROOT_DIR)
    return binary_out


def run_joern_scala_query_for_test(joern_scala_query_for_test_cmd):
    # created a specific function to ease the testing mock-up
    output = subprocess.check_output(joern_scala_query_for_test_cmd, shell=True).decode('utf-8-sig')
    return output


def run_generate_cpg_cmd(gen_cpg_with_params_cmd: str):
    # created a specific function to ease the testing mock-up
    output = subprocess.check_output(gen_cpg_with_params_cmd, shell=True).decode('utf-8-sig')
    return output


def run_discovery_rule(cpg: Path, discovery_rule: Path, discovery_method: str) -> Tuple[str, str, list[Dict]]:
    if discovery_method == "joern":
        run_joern_scala_query = f"joern --script {discovery_rule} --params name={cpg}"
        try:
            logger.info(f"Discovery - rule execution: {run_joern_scala_query}")
            raw_joern_output = subprocess.check_output(run_joern_scala_query, shell=True)
            if isinstance(raw_joern_output, bytes):
                joern_output: str = raw_joern_output.decode('utf-8-sig')
            else:
                joern_output: str = raw_joern_output
            logger.info(f"Discovery - rule raw output: {joern_output}")
        except subprocess.CalledProcessError as e:
            ee = JoernQueryError(e)
            logger.exception(ee)
            raise ee

        splitted_elements = joern_output[1:-1].split(",")
        cpg_file_name: str = splitted_elements[0]
        query_name: str = splitted_elements[1]
        findings_str: str = joern_output.split("," + query_name + ",")[1][:-2]
        findings: list[Dict] = json.loads(findings_str)
        return cpg_file_name, query_name, findings
    else:
        e = DiscoveryMethodNotSupported(discovery_method=discovery_method)
        logger.exception(e)
        raise e


# TODO: refactoring needed. Even more important, we do not want to run the same discovery rule (actually, the same
#  Joern rule of the discovery rule) more than once. E.g., there may be a pattern instance not supported by many tools,
#  so discovery by tool is not the right way...
def discovery_for_tool(cpg: Path, pattern_instances: list[Measurement], tool: Dict, language: str,
                       tp_lib_dir: Path):
    if tool is {}:
        pattern_not_supported_by_tool: list[Measurement] = pattern_instances
    else:
        pattern_not_supported_by_tool: list[Measurement] = list(
            filter(lambda meas: not meas.result and meas.tool == tool["name"], pattern_instances)
        )

    collected_discovery_rules: list[Tuple[Path, Measurement]] = []
    discovery_rules_to_run: Dict = {}
    findings: list[Dict] = []
    for pattern_meas in pattern_not_supported_by_tool:
        instance_dir: str = utils.get_instance_dir_name_from_pattern(
            pattern_meas.instance.name,
            pattern_meas.instance.pattern_id,
            pattern_meas.instance.instance_id)
        pattern_dir: str = utils.get_pattern_dir_name_from_name(
            pattern_meas.instance.name,
            pattern_meas.instance.pattern_id)
        discovery_rule: Path = (
                tp_lib_dir / language / pattern_dir / instance_dir / pattern_meas.instance.discovery_rule).resolve()

        collected_discovery_rules.append((discovery_rule, pattern_meas))

    for d in collected_discovery_rules:
        discovery_rules_to_run[d[0]] = []

    for d in collected_discovery_rules:
        discovery_rules_to_run[d[0]] = discovery_rules_to_run[d[0]] + [d[1]]

    for discovery_rule in discovery_rules_to_run.keys():
        pattern_meas = discovery_rules_to_run[discovery_rule][0]
        try:
            cpg_file_name, query_name, findings_for_pattern = run_discovery_rule(
                cpg, discovery_rule,
                pattern_meas.instance.discovery_method
            )

            findings_for_pattern_refined: list[Dict] = []
            for f in findings_for_pattern:
                f_ref = {
                    "filename": f["filename"],
                    "methodFullName": f["methodFullName"],
                    "lineNumber": f["lineNumber"],
                    "patternId": pattern_meas.instance.pattern_id,
                    "instanceId": [d.instance.instance_id for d in discovery_rules_to_run[discovery_rule]],
                    "patternName": pattern_meas.instance.name,
                    "queryFile": str(discovery_rule)

                }

                findings_for_pattern_refined.append(f_ref)

            findings = findings + findings_for_pattern_refined

        except DiscoveryMethodNotSupported as e:
            print(
                f"{pattern_meas.instance.instance_id}_instance_{pattern_meas.instance.pattern_id}_{pattern_meas.instance.name}: {e}",
                file=sys.stderr)

    return findings


def discovery(src_dir: Path, l_tp_id: list[int], tp_lib_path: Path, itools: list[Dict],
              language: str,
              build_name: str,
              disc_output_dir: Path,
              timeout_sec: int = 0):
    logger.info("Discovery for patterns started...")
    cpg: Path = generate_cpg(src_dir, language, build_name, disc_output_dir, timeout_sec=timeout_sec)
    tools = utils.filter_sast_tools(itools, language)

    # # TODO: LC hereafter an initial idea of fixing/refactoring...to be continued...
    # ns_tools = [t for t in itools if t not in tools]
    # if ns_tools:
    #     logger.warning(
    #         f"Some of the tools do not support the {language} language: {ns_tools}. These tools will just be ignored for the discovery.")
    # if tools:
    #     for tp_id in l_tp_id:
    #         d_tp_meas = utils.get_measurements_for_pattern(tp_id, tp_lib_path, language_filter=language, tools_filter=tools, only_latest=True)
    #         if not d_tp_meas:
    #             logger.warning(f"No measurements associated to {language} pattern id {tp_id}. Run `tpframework measure -l {language} -p {tp_id} -w 2`")
    #             continue
    #         d_tpi_id = utils.list_pattern_instances_by_pattern_id(tp_id)
    #         for tpi_id in d_tpi_id:
    #             if not tpi_id in d_tp_meas:
    #                 logger.warning(
    #                     f"No measurements associated to {language} pattern id {tp_id} instance id {tpi_id}.")
    #                 continue
    #             for t in tools:
    #                 if t not in d_tp_meas[tpi_id]:
    #                     logger.warning(
    #                         f"No measurements for tool {t} associated to {language} pattern id {tp_id} instance id {tpi_id}.")
    #                     continue
    #                 any( d_tp_meas[tpi_id][t][0] == for t in tools)
    #
    ###########

    meas_lang_dir: Path = utils.get_measurement_dir_for_language(tp_lib_path, language)
    dirs = list(meas_lang_dir.iterdir())
    meas_p_id_path_list: Dict = dict(zip(
        map(lambda d: utils.get_id_from_name(d.name), dirs),
        dirs
    ))

    # Get input patterns' paths and then use utils to read from pattern the instances
    # p_lang_dir: Path = tp_lib_dir / language
    # p_id_path_list: Dict = dict(zip(
    #     map(lambda d: int(d.name.split("_")[0]), list(p_lang_dir.iterdir())),
    #     list(p_lang_dir.iterdir())
    # ))

    last_meas: list[Measurement] = []

    l_measured_tp_id = []
    l_not_measured_tp_id = []
    for p_id in l_tp_id:
        try:
            p_path: Path = Path(meas_p_id_path_list[p_id])
            l_measured_tp_id.append(p_id)
        except KeyError:
            e = MeasurementNotFound(p_id)
            logger.warning(f"{e.message} The discovery process tries to continue for the other patterns (if any)...")
            l_not_measured_tp_id.append(p_id)
            continue
        meas_inst_path_list = list(p_path.iterdir())
        for inst_path in meas_inst_path_list:
            last_meas = last_meas + measurement.load_from_metadata(
                utils.get_last_measurement_for_pattern_instance(inst_path), language)

    findings_for_tools: list[Dict] = []
    if tools is []:
        discovery_for_tool(cpg, last_meas, {}, language, tp_lib_path)
    else:
        for tool in tools:
            findings_for_tools = findings_for_tools + discovery_for_tool(cpg, last_meas, tool, language, tp_lib_path)

    for f in findings_for_tools:
        f["instanceId"] = (''.join(f'{iid}, ' for iid in f["instanceId"]))[:-2]

    findings: list[Dict] = [dict(t) for t in {tuple(d.items()) for d in findings_for_tools}]

    ofile = disc_output_dir / f"discovery_{build_name}.csv"
    fields = ["filename", "lineNumber", "methodFullName", "patternId", "instanceId", "patternName", "queryFile"]
    utils.write_csv_file(ofile, fields, findings)
    logger.info("Discovery for patterns completed.")
    d_results = {
        "discovery_result_file": str(ofile),
        "used_measured_patterns_ids": l_measured_tp_id,
        "ignored_not_measured_patterns_ids": l_not_measured_tp_id
    }
    return d_results


def manual_discovery(src_dir: Path, discovery_method: str, discovery_rules: list[Path], language: str,
                     build_name: str, disc_output_dir: Path,
                     timeout_sec: int = 0):
    logger.info("Execution of specific discovery rules started...")
    cpg: Path = generate_cpg(src_dir, language, build_name, disc_output_dir, timeout_sec=timeout_sec)
    findings: list[dict] = []
    for discovery_rule in discovery_rules:
        try:
            cpg_file_name, query_name, findings_for_rule = run_discovery_rule(cpg, discovery_rule, discovery_method)
            if len(findings_for_rule) == 0:
                findings.append({
                    "filename": None,
                    "methodFullName": None,
                    "lineNumber": None,
                    "queryName": query_name,
                    "queryFile": str(discovery_rule),
                    "result": "NO_RESULT"
                })

            for f in findings_for_rule:
                if any(k not in f for k in mand_finding_joern_keys):
                    error = f"Discovery - finding {f} does not include some mandatory keys ({mand_finding_joern_keys}). Please fix the rule and re-run. Often this amount to use `location.toJson`"
                    logger.error(error)
                    raise JoernQueryError(error)
                findings.append({
                    "filename": f["filename"],
                    "methodFullName": f["methodFullName"],
                    "lineNumber": f["lineNumber"],
                    "queryName": query_name,
                    "queryFile": str(discovery_rule),
                    "result": None
                })
        except JoernQueryError as e:
            findings.append({
                "filename": None,
                "methodFullName": None,
                "lineNumber": None,
                "queryName": None,
                "queryFile": str(discovery_rule),
                "result": e.message
            })
            continue

    ofile = disc_output_dir / f"manual_discovery_{build_name}.csv"
    fields = ["filename", "lineNumber", "methodFullName", "queryName", "queryFile", "result"]
    utils.write_csv_file(ofile, fields, findings)
    logger.info("Execution of specific discovery rules completed.")


def get_discovery_build_name_and_dir(src_dir: Path, language: str, output_dir: Path, manual=False):
    now = datetime.now()
    build_name: str = utils.build_timestamp_language_name(src_dir.name, language, now)
    if manual:
        op = "manual_discovery"
    else:
        op = "discovery"
    disc_output_dir = output_dir / f"{op}_{build_name}"
    disc_output_dir.mkdir(parents=True, exist_ok=True)
    return build_name, disc_output_dir
