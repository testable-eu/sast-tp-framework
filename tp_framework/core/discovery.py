import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Tuple
from copy import copy

import logging
from core import loggermgr

logger = logging.getLogger(loggermgr.logger_name(__name__))

import config
from core import utils, measurement
from core.pattern import Pattern
from core.exceptions import DiscoveryMethodNotSupported, MeasurementNotFound, CPGGenerationError, \
    CPGLanguageNotSupported, DiscoveryRuleError, DiscoveryRuleParsingResultError, InvalidSastTools
from core.measurement import Measurement

from core.instance import Instance
from core.pattern import Pattern

# mand_finding_joern_keys = ["filename", "methodFullName", "lineNumber"]
mand_finding_joern_keys = ["filename", "lineNumber"]

discovery_result_strings = {
    "no_discovery": "NO_DISCOVERY",
    "discovery": "DISCOVERY",
    "error": "ERROR_DISCOVERY"
}


def generate_cpg(rel_src_dir_path: Path, language: str, build_name: str, output_dir: Path,
                 timeout_sec: int = 0) -> Path:
    logger.info(f"Generation of CPG for {rel_src_dir_path}: started...")
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

    # related #46
    inst_dir: str = language_cpg_conf['installation_dir']
    if inst_dir.startswith("/"):
        working_dir = Path(inst_dir)
    else:
        working_dir = config.ROOT_DIR / inst_dir
    #
    try:
        cpg_gen_output = run_generate_cpg_cmd(gen_cpg_with_params_cmd, working_dir)
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
        logger.debug(
            "CPG generation failed: exception while loading the CPG in Joern, CPG generation command was successful")
        rs = CPGGenerationError()
        logger.exception(rs)
        raise rs
    # os.chdir(config.ROOT_DIR) # it should not be necessary anymore after changes done for #46
    logger.info(f"Generation of CPG for {rel_src_dir_path}: done.")
    return binary_out


def run_joern_scala_query_for_test(joern_scala_query_for_test_cmd):
    # created a specific function to ease the testing mock-up
    output = subprocess.check_output(joern_scala_query_for_test_cmd, shell=True).decode('utf-8-sig')
    return output


def run_generate_cpg_cmd(gen_cpg_with_params_cmd: str, working_dir: Path):
    # created a specific function to ease the testing mock-up
    curr_working_dir = os.getcwd()
    os.chdir(working_dir)
    try:
        output = subprocess.check_output(gen_cpg_with_params_cmd, shell=True).decode('utf-8-sig')
        os.chdir(curr_working_dir)
    except Exception as e:
        os.chdir(curr_working_dir)
        raise e
    return output


def run_joern_discovery_rule_cmd(run_joern_scala_query: str):
    output = subprocess.check_output(run_joern_scala_query, shell=True)
    return output


def run_joern_discovery_rule(cpg: Path, discovery_rule: Path) -> Tuple[str, str, list[Dict]]:
    logger.debug(f"Discovery - joern rule execution to be executed: {cpg}, {discovery_rule}")
    run_joern_scala_query = f"joern --script {discovery_rule} --params name={cpg}"
    try:
        logger.info(f"Discovery - joern rule execution started: {run_joern_scala_query}")
        raw_joern_output = run_joern_discovery_rule_cmd(run_joern_scala_query)
        if isinstance(raw_joern_output, bytes):
            joern_output: str = raw_joern_output.decode('utf-8-sig')
        else:
            joern_output: str = raw_joern_output
        logger.info(f"Discovery - joern rule raw output: {joern_output}")
    except subprocess.CalledProcessError as e:
        ee = DiscoveryRuleError(
            "Failed in either executing the joern discovery rule or fetching its raw output" + utils.get_exception_message(
                e))
        logger.exception(ee)
        raise ee
    # Parsing Joern output
    try:
        splitted_elements = joern_output[1:-1].split(",")
        cpg_file_name: str = splitted_elements[0]
        query_name: str = splitted_elements[1]
        findings_str: str = joern_output.split("," + query_name + ",")[1][:-2]
        findings: list[Dict] = json.loads(findings_str)
        logger.info(f"Discovery - rule execution done and raw output parsed.")
        return cpg_file_name, query_name, findings
    except Exception as e:
        ee = DiscoveryRuleParsingResultError(
            "Failed in parsing the results of the discovery rule. " + utils.get_exception_message(e))
        logger.exception(ee)
        raise ee


def patch_PHP_discovery_rule(discovery_rule: Path, language: str, output_dir: Path = None):
    if language != "PHP":
        return discovery_rule
    with open(discovery_rule) as ifile:
        # TODO: to be continued
        t_str = ".location.toJson);"
        p_str = ".repeat(_.astParent)(_.until(_.filter(x => x.lineNumber.getOrElse(-1) != -1))).location.toJson);"
        lines = ifile.readlines()
        newlines = []
        changed = False
        for l in lines:
            newl = l.replace(t_str, p_str) if re.match('\s*val x\d+ = \(name, "[^"]+", cpg\.call.*(\.location\.toJson)\);\s*', l) else l
            newlines.append(newl)
            if newl != l:
                changed = True
        if not changed:
            return discovery_rule
        if not output_dir:
            output_dir = discovery_rule.parent
        new_discovery_rule = output_dir / str(config.PATCHED_PREFIX + discovery_rule.name)
        with open(new_discovery_rule, "w") as ofile:
            ofile.writelines(newlines)
        return new_discovery_rule


def process_joern_discovery_rule_findings(discovery_rule: Path, query_name: str, raw_findings) -> list[dict]:
    if not raw_findings:
        return [{
            "discovery": False,
            "filename": None,
            "methodFullName": None,
            "lineNumber": None,
            "queryFile": str(discovery_rule),
            "queryName": query_name
        }]
    findings = []
    for f in raw_findings:
        if any(k not in f for k in mand_finding_joern_keys):
            error = f"Discovery - finding {f} does not include some mandatory keys ({mand_finding_joern_keys}). Please fix the rule {discovery_rule} and re-run. Often this amount to use `location.toJson`"
            logger.error(error)
            # raise DiscoveryRuleError(error)
            continue
        f_ref = {
            "discovery": True,
            "filename": f["filename"],
            "methodFullName": f["methodFullName"] if "methodFullName" in f else None,
            "lineNumber": f["lineNumber"],
            "queryFile": str(discovery_rule),
            "queryName": query_name
        }
        findings.append(f_ref)
    return findings


def run_and_process_discovery_rule(cpg: Path, discovery_rule: Path,
                                   discovery_method: str = config.DEFAULT_DISCOVERY_METHOD):
    default_discovery_method = config.DEFAULT_DISCOVERY_METHOD
    if not discovery_method and discovery_rule.suffix == utils.get_discovery_rule_ext(default_discovery_method):
        logger.warning(
            f"No discovery method has been specified. Likely you need to modify the discovery->method property in the JSON file of the pattern instance related to the discovery rule {discovery_rule}. We will continue with the default discovery method for Scala discovery rules (aka '{default_discovery_method}').")
        discovery_method = default_discovery_method
    if discovery_method == "joern":
        cpg_file_name, query_name, raw_findings = run_joern_discovery_rule(cpg, discovery_rule)
        findings = process_joern_discovery_rule_findings(discovery_rule, query_name, raw_findings)
        return findings
    else:
        e = DiscoveryMethodNotSupported(discovery_method=discovery_method)
        logger.exception(e)
        raise e


############################################################################
# Pattern driven discovery
############################################################################
# Methods hereafter rely on/generate the following data structure
# {tp_id:
#     "measurement_found": bool,
#     "instances": {
#         tpi_id: {
#             "instance": instance.Instance,
#             "measurement": "supported | not_found | not_supported",
#             "jsonpath": Path,
#             "discovery": {
#                 "method" : "joern | ..."
#                 "rule_accuracy": "FP | FN | FPFN | Perfect",
#                 "rule_hash": hash
#                 "rule_already_executed": bool
#                 "results": [{
#                         "discovery": bool,
#                         "filename": "myfile.php"
#                         "methodFullName": "funcFoo()",
#                         "lineNumber": 133,
#                         "queryFile": "path/to/query",
#                         "queryName": "1_static_variables_iall"},
#                             {}, ..]
#                 }}}}}

def discovery(src_dir: Path, l_tp_id: list[int], tp_lib_path: Path, itools: list[Dict],
              language: str,
              build_name: str,
              disc_output_dir: Path,
              timeout_sec: int = 0,
              ignore=False) -> Dict:
    logger.info("Discovery for patterns started...")
    # TODO: to support multiple discovery methods the following would need major refactoring.
    # - CPG is specific to Joern
    # - each discovery rule tells which method to use
    # - on the other hand you do not want to compute the CPG multiple times

    cpg: Path = generate_cpg(src_dir, language, build_name, disc_output_dir, timeout_sec=timeout_sec)
    if not ignore:
        return discovery_under_measurement(cpg, l_tp_id, tp_lib_path, itools, language, build_name, disc_output_dir,
                                           timeout_sec=timeout_sec)
    else:
        return discovery_ignore_measurement(cpg, l_tp_id, tp_lib_path, language, build_name, disc_output_dir,
                                            timeout_sec=timeout_sec)


def discovery_under_measurement(cpg: Path, l_tp_id: list[int], tp_lib: Path, itools: list[Dict],
                                language: str,
                                build_name: str,
                                disc_output_dir: Path,
                                timeout_sec: int = 0) -> Dict:
    # filter over tools
    tools = utils.filter_sast_tools(itools, language)
    if not tools:
        e = InvalidSastTools()
        logger.exception(e)
        raise e
    # Make end-user aware of the tools that do not support the targeted language and that thus will be ignored
    ns_tools = [t for t in itools if t not in tools]
    if ns_tools:
        logger.warning(
            f"Some of the tools do not support the {language} language: {ns_tools}. These tools will just be ignored for the discovery.")
    # map patterns to measurement dirs
    meas_lang_dir: Path = utils.get_measurement_dir_for_language(tp_lib, language)
    dirs = utils.list_dirs_only(meas_lang_dir)
    meas_p_id_path_list: Dict = dict(zip(
        map(lambda d: utils.get_id_from_name(d.name), dirs),
        dirs
    ))
    d_res = {}  # result data structure set to empty
    # computing not supported testability patterns (tp) to be discovered
    for tp_id in l_tp_id:
        msgpre = f"pattern {tp_id} - "
        msgpost = "Discovery tries to continue for the other patterns/instances..."
        try:
            meas_tp_path: Path = Path(meas_p_id_path_list[tp_id])
            d_res[tp_id] = {
                "measurement_found": True
            }
            # l_measured_tp_id.append(tp_id)
        except KeyError:
            e = MeasurementNotFound(tp_id)
            logger.warning(
                f"{msgpre}{utils.get_exception_message(e)}{msgpost}")
            d_res[tp_id] = {
                "measurement_found": False
            }
            # l_not_measured_tp_id.append(tp_id)
            continue
        target_pattern = Pattern.init_from_id_and_language(tp_id, language, tp_lib)
        l_meas_tpi_path = utils.list_dirs_only(meas_tp_path)
        # computing not supported tp instances (tpi) to be discovered
        d_res_tpi = {}
        d_dr_executed = {}
        for tpi in target_pattern.instances:
            msgpre = f"pattern {tp_id} instance {tpi.instance_id} - "
            try:
                meas_tpi_path = utils.get_instance_dir_from_list(tpi.instance_id, l_meas_tpi_path)
            except:
                logger.warning(
                    f"{msgpre}No measurements for this instance. {msgpost}")
                d_res_tpi[tpi.instance_id] = {
                    "measurement": "not_found",
                    "jsonpath": tpi.json_path
                }
                continue
            l_last_meas = measurement.load_measurements(utils.get_last_measurement_for_pattern_instance(meas_tpi_path),
                                                        tp_lib, language)
            meas_tpi_by_tools: list[Measurement] = [meas for meas in l_last_meas if
                                                    measurement.any_tool_matching(meas, tools)]
            if not meas_tpi_by_tools:
                logger.warning(
                    f"{msgpre}No measurements of the tools specified ({[t['name'] + ':' + t['version'] for t in tools]}) for the instance. {msgpost}")
                d_res_tpi[tpi.instance_id] = {
                    "measurement": "not_found",
                    "jsonpath": tpi.json_path
                }
                continue
            tpi_instance = meas_tpi_by_tools[0].instance
            d_tpi = {
                "instance": tpi_instance,
                "measurement": "supported",
                "jsonpath": tpi.json_path,
                "discovery": {}
            }
            # discovery continue iff at least one tool not supporting the tpi
            for tool in tools:
                meas_tpi_by_tool = [meas for meas in meas_tpi_by_tools if measurement.any_tool_matching(meas, [tool])]
                if not meas_tpi_by_tool:
                    logger.warning(
                        f"{msgpre}No measurements of tool {tool['name'] + ':' + tool['version']} for this instance. You may want to run that measurement...")
                    continue
                meas_tpi_not_supported_by_tool = [meas for meas in meas_tpi_by_tool if not meas.result]
                if meas_tpi_not_supported_by_tool:
                    logger.info(
                        f"{msgpre} great, last measurement indicating that the tool {tool['name'] + ':' + tool['version']} does not support the pattern instance. Discovery rule will be run (if any)")
                    d_tpi["measurement"] = "not_supported"
            # discovery per tpi
            measurement_stop: bool = d_tpi["measurement"] not in ["ignore", "not_supported"]
            d_tpi["discovery"] = discovery_for_tpi(tpi_instance, tpi.json_path, cpg, disc_output_dir,
                                                   measurement_stop=measurement_stop, already_executed=d_dr_executed)
            d_res_tpi[tpi.instance_id] = d_tpi
        d_res[tp_id]["instances"] = d_res_tpi

    # post-process results and export them
    d_results = post_process_and_export_results(d_res, build_name, disc_output_dir)
    d_results["tools"] = tools
    d_results["cpg_file"] = str(cpg)
    logger.info("Discovery for patterns completed.")
    return d_results


def discovery_ignore_measurement(cpg: Path, l_tp_id: list[int], tp_lib: Path,
                                 language: str,
                                 build_name: str,
                                 disc_output_dir: Path,
                                 timeout_sec: int = 0) -> Dict:
    d_res = {}  # result data structure set to empty
    # loop over testability patterns (tp) to be discovered
    for tp_id in l_tp_id:
        d_res[tp_id] = {"measurement_found": None}
        target_pattern = Pattern.init_from_id_and_language(tp_id, language, tp_lib)
        # loop over tp instances (tpi) to be discovered
        d_res_tpi = {}
        d_dr_executed = {}
        for instance in target_pattern.instances:
            tpi_json_path = instance.json_path
            d_tpi = {"instance": instance, "measurement": "ignored", "jsonpath": tpi_json_path,
                     "discovery": discovery_for_tpi(instance, tpi_json_path, cpg, disc_output_dir,
                                                    measurement_stop=False, already_executed=d_dr_executed)}
            d_res_tpi[instance.instance_id] = d_tpi
        d_res[tp_id]["instances"] = d_res_tpi

    # post-process results and export them
    d_results = post_process_and_export_results(d_res, build_name, disc_output_dir)
    d_results["cpg_file"] = str(cpg)
    logger.info("Discovery for patterns completed.")
    return d_results


def discovery_for_tpi(tpi_instance: Instance, tpi_json_path: Path, cpg: Path, disc_output_dir: Path,
                      measurement_stop: bool = False, already_executed: dict = {}) -> Dict:
    msgpre = f"pattern {tpi_instance.pattern_id} instance {tpi_instance.instance_id} - "
    d_tpi_discovery = dict.fromkeys(["rule_path", "method", "rule_name", "rule_accuracy", "rule_hash", \
                                     "rule_name", "results", "rule_already_executed"], None)
    # execute the discovery rule
    if not measurement_stop and tpi_instance.discovery_rule:
        # prepare and execute the discovery rule (if not done yet)
        dr = (tpi_json_path.parent / tpi_instance.discovery_rule).resolve()

        logger.info(
            f"{msgpre}prepare discovery rule {dr}...")
        d_tpi_discovery["rule_path"] = str(dr)
        d_tpi_discovery["method"] = tpi_instance.discovery_method
        d_tpi_discovery["rule_accuracy"] = tpi_instance.discovery_rule_accuracy
        d_tpi_discovery["rule_hash"] = utils.get_file_hash(dr)
        if d_tpi_discovery["rule_hash"] not in already_executed:
            logger.info(
                f"{msgpre}running discovery rule...")
            # related to #42
            pdr = patch_PHP_discovery_rule(dr, tpi_instance.language, output_dir=disc_output_dir)
            try:
                findings = run_and_process_discovery_rule(cpg, pdr, discovery_method=d_tpi_discovery["method"])
                d_tpi_discovery["results"] = findings
                d_tpi_discovery["rule_already_executed"] = False
            except DiscoveryMethodNotSupported as e:
                d_tpi_discovery["results"] = None
                already_executed[d_tpi_discovery["rule_hash"]] = None
                logger.error(
                    f"{msgpre}Discovery rule failure for this instance: {e}")
                # JoernQueryError(e)
                # JoernQueryParsingResultError(e)
            already_executed[d_tpi_discovery["rule_hash"]] = findings
            logger.info(
                f"{msgpre} discovery rule executed.")

        else:
            logger.info(
                f"{msgpre}discovery rule {dr} was already run. We will use the same result...")
            d_tpi_discovery["rule_already_executed"] = True
            d_tpi_discovery["results"] = already_executed[d_tpi_discovery["rule_hash"]]
    else:
        # no rule to execute
        logger.warning(
            f"{msgpre}No discovery rule for this pattern instance...")
    return d_tpi_discovery


def post_process_and_export_results(d_res: dict, build_name: str, disc_output_dir: Path) -> Dict:
    # "sast_measurement" in ["ignored", "missing", "supported", "not_supported"]
    fields = ["patternId", "instanceId", "instanceName", "sast_measurement",
              "method", "queryFile", "queryHash", "queryName", "queryAccuracy",
              "queryAlreadyExecuted", "discovery", "filename", "lineNumber", "methodFullName"]
    rows = []
    for tp_id in d_res:
        if d_res[tp_id]["measurement_found"] is False:
            rows.append(
                {
                    "patternId": tp_id,
                    "instanceId": None,
                    "instanceName": None,
                    "sast_measurement": "missing",
                    "method": None,
                    "queryFile": None,
                    "queryHash": None,
                    "queryName": None,
                    "queryAccuracy": None,
                    "queryAlreadyExecuted": None,
                    "discovery": None,
                    "filename": None,
                    "lineNumber": None,
                    "methodFullName": None
                })
            continue
        for tpi_id in d_res[tp_id]["instances"]:
            tpi_data = d_res[tp_id]["instances"][tpi_id]
            if tpi_data["measurement"] not in ["not_supported", "ignored"]:
                rows.append(
                    {
                        "patternId": tp_id,
                        "instanceId": tpi_id,
                        "instanceName": tpi_data["instance"].name,
                        "sast_measurement": tpi_data["measurement"],
                        "method": None,
                        "queryFile": None,
                        "queryHash": None,
                        "queryName": None,
                        "queryAccuracy": None,
                        "queryAlreadyExecuted": None,
                        "discovery": None,
                        "filename": None,
                        "lineNumber": None,
                        "methodFullName": None
                    })
                continue
            else:
                disc_data = tpi_data["discovery"]
                base = {
                    "patternId": tp_id,
                    "instanceId": tpi_id,
                    "instanceName": tpi_data["instance"].name,
                    "sast_measurement": tpi_data["measurement"],
                    "method": disc_data["method"],
                    "queryFile": disc_data["rule_path"],
                    "queryHash": disc_data["rule_hash"],
                    "queryName": None,
                    "queryAccuracy": disc_data["rule_accuracy"],
                    "queryAlreadyExecuted": disc_data["rule_already_executed"],
                    "discovery": None,
                    "filename": None,
                    "lineNumber": None,
                    "methodFullName": None
                }
                if disc_data["results"] is None:
                    base["discovery"] = "failure"
                    rows.append(base)
                else:
                    for f in disc_data["results"]:
                        try:
                            row = copy(base)
                            row["discovery"] = f["discovery"]
                            row["queryName"] = f["queryName"]
                            if f["discovery"]:
                                row["filename"] = f["filename"]
                                row["lineNumber"] = f["lineNumber"]
                                row["methodFullName"] = f["methodFullName"]
                            rows.append(row)
                        except Exception as e:
                            logger.error("Hell no")
                            pass
    ofile = disc_output_dir / f"discovery_{build_name}.csv"
    utils.write_csv_file(ofile, fields, rows)
    d_results = {
        "discovery_result_file": str(ofile),
        "results": d_res
    }
    return d_results


def get_ignored_tp_from_results(d_res):
    return [f"p{tp_id}" for tp_id in d_res["results"] if d_res["results"][tp_id]['measurement_found'] is False]


def get_ignored_tpi_from_results(d_res, ignored_as):
    return [f"p{tp_id}_i{tpi_id}"
            for tp_id in d_res["results"]
            for tpi_id in d_res["results"][tp_id]['instances']
            if d_res["results"][tp_id]['measurement_found'] and
            d_res["results"][tp_id]['instances'][tpi_id]["measurement"] == ignored_as]


def get_ignored_tpi_from_results(d_res, ignored_as):
    return [f"p{tp_id}_i{tpi_id}"
            for tp_id in [tp_id for tp_id in d_res["results"] if d_res["results"][tp_id]['measurement_found']]
            for tpi_id in d_res["results"][tp_id]['instances']
            if d_res["results"][tp_id]['instances'][tpi_id]["measurement"] == ignored_as]


def get_unsuccessful_discovery_tpi_from_results(d_res):
    return [f"p{tp_id}_i{tpi_id}"
            for tp_id in [tp_id for tp_id in d_res["results"] if d_res["results"][tp_id]['measurement_found'] is not False]
            for tpi_id in d_res["results"][tp_id]['instances']
            if d_res["results"][tp_id]['instances'][tpi_id]["measurement"] in ["not_supported", "ignored"] and
            d_res["results"][tp_id]['instances'][tpi_id]["discovery"]["results"] is None]


def get_successful_discovery_tpi_from_results(d_res):
    return [f"p{tp_id}_i{tpi_id}"
            for tp_id in [tp_id for tp_id in d_res["results"] if d_res["results"][tp_id]['measurement_found'] is not False]
            for tpi_id in d_res["results"][tp_id]['instances']
            if d_res["results"][tp_id]['instances'][tpi_id]["measurement"] in ["not_supported", "ignored"] and
            d_res["results"][tp_id]['instances'][tpi_id]["discovery"]["results"] is not None]


def get_num_discovery_findings_from_results(d_res):
    n = 0
    for tp_id in d_res["results"]:
        if d_res["results"][tp_id]['measurement_found'] is False:
            continue
        for tpi_id in d_res["results"][tp_id]['instances']:
            tpi_data = d_res["results"][tp_id]['instances'][tpi_id]
            if tpi_data["measurement"] in ["not_supported", "ignored"]  and tpi_data["discovery"]["results"] is not None:
                for r in tpi_data["discovery"]["results"]:
                    if r["discovery"] == True:
                        n += 1
    return n
############################################################################


############################################################################
# Manual discovery: driven by mere discovery rules whether they are associated with patterns or not
############################################################################

def manual_discovery(src_dir: Path, discovery_method: str, discovery_rules: list[Path], language: str,
                     build_name: str, disc_output_dir: Path,
                     timeout_sec: int = 0) -> Dict:
    # TODO: only support Joern as discovery method, discovery method param is thus irrelevant
    # - refactor to support additional discovery method.
    # - maybe the discovery_method can be simply decided from the discovery rule extension?
    logger.info("Execution of specific discovery rules started...")
    cpg: Path = generate_cpg(src_dir, language, build_name, disc_output_dir, timeout_sec=timeout_sec)
    findings: list[dict] = []
    failed = []
    for discovery_rule in discovery_rules:
        try:
            # related to #42
            patched_discovery_rule = patch_PHP_discovery_rule(discovery_rule, language, output_dir=disc_output_dir)
            #
            cpg_file_name, query_name, findings_for_rule = run_joern_discovery_rule(
                cpg, patched_discovery_rule)
            logger.info("Parsing the results of specific discovery rules started...")
            try:
                if len(findings_for_rule) == 0:
                    findings.append({
                        "filename": None,
                        "methodFullName": None,
                        "lineNumber": None,
                        "queryName": query_name,
                        "queryFile": str(discovery_rule),
                        "result": discovery_result_strings["no_discovery"]
                    })
            except Exception as e:
                ee = DiscoveryRuleParsingResultError(
                    f"Failed in parsing the findings from the discovery rule. Exception raised: {utils.get_exception_message(e)}")
                logger.exception(ee)
                raise ee

            for f in findings_for_rule:
                if any(k not in f for k in mand_finding_joern_keys):
                    error = f"Discovery - finding {f} does not include some mandatory keys ({mand_finding_joern_keys}). Please fix the rule and re-run. Often this amount to use `location.toJson`"
                    logger.error(error)
                    raise DiscoveryRuleError(error)
                findings.append({
                    "filename": f["filename"],
                    "methodFullName": f["methodFullName"] if "methodFullName" in f else None,
                    "lineNumber": f["lineNumber"],
                    "queryName": query_name,
                    "queryFile": str(discovery_rule),
                    "result": discovery_result_strings["discovery"]
                })
        except Exception as e:
            findings.append({
                "filename": None,
                "methodFullName": None,
                "lineNumber": None,
                "queryName": None,
                "queryFile": str(discovery_rule),
                "result": discovery_result_strings["error"] + ". " + utils.get_exception_message(e)
            })
            failed.append(discovery_rule)
            continue

    ofile = disc_output_dir / f"manual_discovery_{build_name}.csv"
    fields = ["filename", "lineNumber", "methodFullName", "queryName", "queryFile", "result"]
    utils.write_csv_file(ofile, fields, findings)
    d_results = {
        "manual_discovery_result_file": str(ofile),
        "cpg_file:": str(cpg),
        "failed_discovery_rules": failed,
        "findings": findings
    }
    logger.info("Execution of specific discovery rules completed.")
    return d_results


############################################################################
# Check discovery rules: manual discovery of pattern instances' discovery rules over the instances themselves
############################################################################

# check discovery rules
def get_check_discovery_rule_result_header():
    return [
        "pattern_id",
        "instance_id",
        "instance_path",
        "pattern_name",
        "language",
        "discovery_rule",
        "successful"
    ]


def get_check_discovery_rule_result(pattern: Pattern, instance: Instance | None= None, successful="error") -> Dict:
    return {
        "pattern_id": pattern.pattern_id,
        "instance_id": instance.instance_id if instance else None,
        "instance_path": instance.path if instance else None,
        "pattern_name": pattern.name,
        "language": pattern.language,
        "discovery_rule": instance.discovery_rule if instance else None,
        "successful": successful
    }


def check_discovery_rules(language: str, l_tp_id: list[int],
                          timeout_sec: int,
                          tp_lib_path: Path,
                          output_dir: Path
                          ) -> Dict:
    logger.info(f"Check/Test discovery rules for {len(l_tp_id)} patterns: started...")
    results = []
    success = 0
    unsuccess = 0
    missing = 0
    err = 0
    num_patterns = len(l_tp_id)
    for i, tp_id in enumerate(l_tp_id):
        logger.info(utils.get_tp_op_status_string(
            (i + 1, num_patterns, tp_id)  # tp_info
        ))
        try:
            target_pattern = Pattern.init_from_id_and_language(tp_id, language, tp_lib_path)
            num_instances = len(target_pattern.instances)
        except Exception as e:
            # should not happen at all! And should be removed and a list of patterns should be parsed to that function
            logger.warning(
                f"Either pattern id {tp_id} does not exist, or its file system structure is not valid, or its instances cannot be fetched. Exception raised: {utils.get_exception_message(e)}")
            res = get_check_discovery_rule_result(pattern=target_pattern)
            results.append(res)
            err += 1
            continue
        instance: Instance
        for j, instance in enumerate(target_pattern.instances):
            try:
                tpi_id = instance.instance_id
                logger.info(utils.get_tpi_op_status_string(
                    (i + 1, num_patterns, tp_id),
                    t_tpi_info=(j + 1, num_instances, tpi_id)
                ))

                if instance.discovery_rule:
                    dr_path = instance.discovery_rule
                    if not dr_path.is_file():
                        logger.warning(
                            f"Instance {tpi_id} of pattern {tp_id}: the discovery rule {dr_path} does not exist")
                        res = get_check_discovery_rule_result(pattern=target_pattern, instance=instance)
                        results.append(res)
                        err += 1
                        continue

                    target_src = instance.path

                    build_name, disc_output_dir = utils.get_operation_build_name_and_dir(
                        "check_discovery_rules", target_src, language, output_dir)
                    d_results = manual_discovery(target_src, instance.discovery_method, [dr_path], language,
                                                 build_name, disc_output_dir, timeout_sec=timeout_sec)
                    # Inspect the d_results
                    if d_results["findings"] and any(
                            f["result"] == discovery_result_strings["discovery"] for f in d_results["findings"]):
                        res = get_check_discovery_rule_result(pattern=target_pattern, instance=instance, successful="yes")
                        success += 1
                    else:
                        res = get_check_discovery_rule_result(pattern=target_pattern, instance=instance, successful="no")
                        unsuccess += 1
                    results.append(res)
                else:
                    logger.info(
                        f"Instance {tpi_id} of pattern {tp_id}: the discovery rule is not provided for the pattern")
                    res = get_check_discovery_rule_result(pattern=target_pattern, instance=instance, successful="missing")
                    results.append(res)
                    missing += 1
                logger.info(utils.get_tpi_op_status_string(
                    (i + 1, num_patterns, tp_id),
                    t_tpi_info=(j + 1, num_instances, tpi_id),
                    status="done."
                ))
            except Exception as e:
                logger.warning(
                    f"Something went wrong for the instance at {instance.path} of the pattern id {tp_id}. Exception raised: {utils.get_exception_message(e)}")
                res = get_check_discovery_rule_result(pattern=target_pattern, instance=instance)
                results.append(res)
                err += 1
                continue
        logger.info(utils.get_tp_op_status_string(
            (i + 1, num_patterns, tp_id),  # tp_info
            status="done."
        ))
    logger.info(f"Check/Test discovery rules for {num_patterns} patterns: done")
    d_res = {
        "results": results,
        "counters": {
            "successful": success,
            "unsuccessful": unsuccess,
            "missing": missing,
            "errors": err
        }
    }
    return d_res
