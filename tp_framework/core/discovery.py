import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Tuple

import logging
from core import loggermgr
logger = logging.getLogger(loggermgr.logger_name(__name__))

import config
from core import utils, measurement
from core.exceptions import DiscoveryMethodNotSupported, MeasurementNotFound, CPGGenerationError, \
    CPGLanguageNotSupported, DiscoveryRuleError, DiscoveryRuleParsingResultError, InvalidSastTools
from core.measurement import Measurement

from core.instance import Instance, instance_from_dict
from core.pattern import get_pattern_by_pattern_id



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
        logger.debug("CPG generation failed: exception while loading the CPG in Joern, CPG generation command was successful")
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


def run_discovery_rule_cmd(run_joern_scala_query: str):
    output = subprocess.check_output(run_joern_scala_query, shell=True)
    return output


def run_discovery_rule(cpg: Path, discovery_rule: Path, discovery_method: str) -> Tuple[str, str, list[Dict]]:
    logger.debug(f"Discovery - rule execution to be executed: {cpg}, {discovery_rule}, {discovery_method}")
    # related to #36
    default_discovery_method = config.DEFAULT_DISCOVERY_METHOD
    if not discovery_method and discovery_rule.suffix == utils.get_discovery_rule_ext(default_discovery_method):
        logger.warning(
            f"No discovery method has been specified. Likely you need to modify the discovery->method property in the JSON file of the pattern instance related to the discovery rule {discovery_rule}. We will continue with the default discovery method for Scala discovery rules (aka '{default_discovery_method}').")
        discovery_method = default_discovery_method
    #
    if discovery_method == "joern":
        run_joern_scala_query = f"joern --script {discovery_rule} --params name={cpg}"
        try:
            logger.info(f"Discovery - rule execution started: {run_joern_scala_query}")
            raw_joern_output = run_discovery_rule_cmd(run_joern_scala_query)
            if isinstance(raw_joern_output, bytes):
                joern_output: str = raw_joern_output.decode('utf-8-sig')
            else:
                joern_output: str = raw_joern_output
            logger.info(f"Discovery - rule raw output: {joern_output}")
        except subprocess.CalledProcessError as e:
            ee = DiscoveryRuleError("Failed in either executing the discovery rule or fetching its raw output" + utils.get_exception_message(e))
            logger.exception(ee)
            raise ee
        # Parsing Joern results
        try:
            splitted_elements = joern_output[1:-1].split(",")
            cpg_file_name: str = splitted_elements[0]
            query_name: str = splitted_elements[1]
            findings_str: str = joern_output.split("," + query_name + ",")[1][:-2]
            findings: list[Dict] = json.loads(findings_str)
            logger.info(f"Discovery - rule execution done and raw output parsed.")
            return cpg_file_name, query_name, findings
        except Exception as e:
            ee = DiscoveryRuleParsingResultError("Failed in parsing the results of the discovery rule. " + utils.get_exception_message(e))
            logger.exception(ee)
            raise ee
    else:
        e = DiscoveryMethodNotSupported(discovery_method=discovery_method)
        logger.exception(e)
        raise e


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
            newl = l.replace(t_str, p_str)
            newlines.append(newl)
            if newl != l:
                changed = True
        if not changed:
            return discovery_rule
        if not output_dir:
            output_dir = discovery_rule.parent
        new_discovery_rule = output_dir / str("patched_"+discovery_rule.name)
        with open(new_discovery_rule, "w") as ofile:
            ofile.writelines(newlines)
        return new_discovery_rule


# TODO - discovery: refactoring needed. Even more important, we do not want to run the same discovery rule (actually, the same
#  Joern rule of the discovery rule) more than once. E.g., there may be a pattern instance not supported by many tools,
#  so discovery by tool is not the right way...
def discovery_for_tool(cpg: Path, pattern_instances: list[Measurement], tool: Dict, language: str,
                       tp_lib_dir: Path, output_dir: Path = None):
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
            # related to #42
            patched_discovery_rule = patch_PHP_discovery_rule(discovery_rule, language, output_dir=output_dir)
            #
            cpg_file_name, query_name, findings_for_pattern = run_discovery_rule(
                cpg, patched_discovery_rule,
                pattern_meas.instance.discovery_method
            )
        except DiscoveryMethodNotSupported as e:
            logger.error(
                f"Discovery rule failure for {pattern_meas.instance.instance_id}_instance_{pattern_meas.instance.pattern_id}_{pattern_meas.instance.name}: {e}")
            continue
        ## JoernQueryError(e)
        ## JoernQueryParsingResultError(e)
        findings_for_pattern_refined: list[Dict] = []
        for f in findings_for_pattern:
            if any(k not in f for k in mand_finding_joern_keys):
                error = f"Discovery - finding {f} does not include some mandatory keys ({mand_finding_joern_keys}). Please fix the rule and re-run. Often this amount to use `location.toJson`"
                logger.error(error)
                # raise DiscoveryRuleError(error)
                continue
            f_ref = {
                "filename": f["filename"],
                "methodFullName": f["methodFullName"] if "methodFullName" in f else None,
                "lineNumber": f["lineNumber"],
                "patternId": pattern_meas.instance.pattern_id,
                "instanceId": [d.instance.instance_id for d in discovery_rules_to_run[discovery_rule]],
                "patternName": pattern_meas.instance.name,
                "queryFile": str(discovery_rule)

            }

            findings_for_pattern_refined.append(f_ref)

        findings = findings + findings_for_pattern_refined

    return findings


def discovery(src_dir: Path, l_tp_id: list[int], tp_lib_path: Path, itools: list[Dict],
              language: str,
              build_name: str,
              disc_output_dir: Path,
              timeout_sec: int = 0,
              ignore=False) -> Dict:
    logger.info("Discovery for patterns started...")
    cpg: Path = generate_cpg(src_dir, language, build_name, disc_output_dir, timeout_sec=timeout_sec)

    tools = utils.filter_sast_tools(itools, language)
    if not tools:
        e = InvalidSastTools()
        logger.exception(e)
        raise e
    ns_tools = [t for t in itools if t not in tools]
    if ns_tools:
        logger.warning(
            f"Some of the tools do not support the {language} language: {ns_tools}. These tools will just be ignored for the discovery.")

    # TODO - discovery:
    ## - LC hereafter an initial idea of fixing/refactoring...to be continued...
    ## - the argument `ignore` can only be considered after refactoring. At the moment the code is too intertwined to do so...
    ## - while refactoring make sure we can report in the results about each one of the discovery rule, even when no discoveries are reported
    # for tp_id in l_tp_id:
    #     d_tp_meas = utils.get_measurements_for_pattern(tp_id, tp_lib_path, language_filter=language, tools_filter=tools, only_latest=True)
    #     if not d_tp_meas:
    #         logger.warning(f"No measurements associated to {language} pattern id {tp_id}. Run `tpframework measure -l {language} -p {tp_id} -w 2`")
    #         continue
    #     d_tpi_id = utils.list_pattern_instances_by_pattern_id(tp_id)
    #     for tpi_id in d_tpi_id:
    #         if not tpi_id in d_tp_meas:
    #             logger.warning(
    #                 f"No measurements associated to {language} pattern id {tp_id} instance id {tpi_id}.")
    #             continue
    #         for t in tools:
    #             if t not in d_tp_meas[tpi_id]:
    #                 logger.warning(
    #                     f"No measurements for tool {t} associated to {language} pattern id {tp_id} instance id {tpi_id}.")
    #                 continue
    #             any( d_tp_meas[tpi_id][t][0] == for t in tools)
    # ###########

    meas_lang_dir: Path = utils.get_measurement_dir_for_language(tp_lib_path, language)
    dirs = []
    if meas_lang_dir.is_dir():
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
            logger.warning(f"{utils.get_exception_message(e)} The discovery process tries to continue for the other patterns (if any)...")
            l_not_measured_tp_id.append(p_id)
            continue
        meas_inst_path_list = list(p_path.iterdir())
        for inst_path in meas_inst_path_list:
            last_meas = last_meas + measurement.load_from_metadata(
                utils.get_last_measurement_for_pattern_instance(inst_path), language)

    findings_for_tools: list[Dict] = []
    if tools is []:
        discovery_for_tool(cpg, last_meas, {}, language, tp_lib_path, output_dir=disc_output_dir)
    else:
        for tool in tools:
            findings_for_tools = findings_for_tools + discovery_for_tool(cpg, last_meas, tool, language, tp_lib_path, output_dir=disc_output_dir)

    for f in findings_for_tools:
        f["instanceId"] = (''.join(f'{iid}, ' for iid in f["instanceId"]))[:-2]

    findings: list[Dict] = [dict(t) for t in {tuple(d.items()) for d in findings_for_tools}]

    ofile = disc_output_dir / f"discovery_{build_name}.csv"
    fields = ["filename", "lineNumber", "methodFullName", "patternId", "instanceId", "patternName", "queryFile"]
    utils.write_csv_file(ofile, fields, findings)
    d_results = {
        "discovery_result_file": str(ofile),
        "tools": tools,
        "cpg_file:": str(cpg),
        "used_measured_patterns_ids": l_measured_tp_id,
        "ignored_not_measured_patterns_ids": l_not_measured_tp_id,
        "findings": findings
    }
    logger.info("Discovery for patterns completed.")
    return d_results


def manual_discovery(src_dir: Path, discovery_method: str, discovery_rules: list[Path], language: str,
                     build_name: str, disc_output_dir: Path,
                     timeout_sec: int = 0) -> Dict:
    logger.info("Execution of specific discovery rules started...")
    cpg: Path = generate_cpg(src_dir, language, build_name, disc_output_dir, timeout_sec=timeout_sec)
    findings: list[dict] = []
    failed = []
    for discovery_rule in discovery_rules:
        try:
            # related to #42
            patched_discovery_rule = patch_PHP_discovery_rule(discovery_rule, language, output_dir=disc_output_dir)
            #
            cpg_file_name, query_name, findings_for_rule = run_discovery_rule(
                cpg, patched_discovery_rule, discovery_method)
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


def get_check_discovery_rule_result(pattern_id, language,
                                    instance_id=None, instance_path=None, pattern_name=None,
                                    discovery_rule=None, successful="error") -> Dict:
    return {
        "pattern_id": pattern_id,
        "instance_id": instance_id,
        "instance_path": instance_path,
        "pattern_name": pattern_name,
        "language": language,
        "discovery_rule": discovery_rule,
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
    for i, tp_id in enumerate(l_tp_id):
        logger.info(utils.get_tp_op_status_string(
            (i + 1, len(l_tp_id), tp_id) # tp_info
        ))
        try:
            target_tp, p_dir = get_pattern_by_pattern_id(language, tp_id, tp_lib_path)
            l_tpi_dir: list[Path] = utils.list_pattern_instances_by_pattern_id(
                language, tp_id, tp_lib_path
            )
        except Exception as e:
            logger.warning(f"Either pattern id {tp_id} does not exist, or its file system structure is not valid, or its instances cannot be fetched. Exception raised: {utils.get_exception_message(e)}")
            res = get_check_discovery_rule_result(tp_id, language)
            results.append(res)
            err += 1
            continue
        for j, path in enumerate(l_tpi_dir):
            try:
                target_src = path.parent
                # TODO: use a function to load an instance, in general it looks to me we are going a bit back and forth
                #       from json and file system.
                #       Also: this loading seems to be used in many other places (e.g., start_add_measurement_for_pattern)...
                with open(path) as instance_json_file:
                    instance_json: Dict = json.load(instance_json_file)

                tpi_id = utils.get_id_from_name(path.name)
                logger.info(utils.get_tpi_op_status_string(
                            (i + 1, len(l_tp_id), tp_id),
                            t_tpi_info=(j+1, len(l_tpi_dir), tpi_id)
                ))
                target_instance: Instance = instance_from_dict(instance_json, target_tp, language, tpi_id)

                if target_instance.discovery_rule:
                    dr_path = target_src / target_instance.discovery_rule
                    if not dr_path.is_file():
                        logger.warning(f"Instance {tpi_id} of pattern {tp_id}: the discovery rule {dr_path} does not exist")
                        res = get_check_discovery_rule_result(tp_id, language, instance_id=tpi_id,
                                                              instance_path=path, discovery_rule=dr_path)
                        results.append(res)
                        err += 1
                        continue

                    build_name, disc_output_dir = utils.get_operation_build_name_and_dir(
                        "check_discovery_rules", target_src, language, output_dir)
                    d_results = manual_discovery(target_src, target_instance.discovery_method, [dr_path], language, build_name, disc_output_dir, timeout_sec=timeout_sec)
                    # Inspect the d_results
                    if d_results["findings"] and any( f["result"] == discovery_result_strings["discovery"] for f in d_results["findings"]):
                        res = get_check_discovery_rule_result(tp_id, language, instance_id=tpi_id,
                                                              instance_path=path, pattern_name=target_tp.name,
                                                              discovery_rule=dr_path, successful="yes")
                        success += 1
                    else:
                        res = get_check_discovery_rule_result(tp_id, language, instance_id=tpi_id,
                                                              instance_path=path, pattern_name=target_tp.name,
                                                              discovery_rule=dr_path, successful="no")
                        unsuccess += 1
                    results.append(res)
                else:
                    logger.info(f"Instance {tpi_id} of pattern {tp_id}: the discovery rule is not provided for the pattern")
                    res = get_check_discovery_rule_result(tp_id, language, instance_id=tpi_id,
                                                          instance_path=path, successful="missing")
                    results.append(res)
                    missing += 1
                logger.info(utils.get_tpi_op_status_string(
                            (i + 1, len(l_tp_id), tp_id),
                            t_tpi_info=(j+1, len(l_tpi_dir), tpi_id),
                            status="done."
                ))
            except Exception as e:
                logger.warning(f"Something went wrong for the instance at {path} of the pattern id {tp_id}. Exception raised: {utils.get_exception_message(e)}")
                res = get_check_discovery_rule_result(tp_id, language, pattern_name=target_tp.name, instance_path=path)
                results.append(res)
                err += 1
                continue
        logger.info(utils.get_tp_op_status_string(
            (i + 1, len(l_tp_id), tp_id), # tp_info
            status="done."
        ))
    logger.info(f"Check/Test discovery rules for {len(l_tp_id)} patterns: done")
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

