import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Tuple
from uuid import uuid1
from copy import copy, deepcopy

import logging
from core import loggermgr

logger = logging.getLogger(loggermgr.logger_name(__name__))

import config
from core import utils, measurement
from core.pattern import Pattern
from core.exceptions import DiscoveryMethodNotSupported, MeasurementNotFound, CPGGenerationError, \
    CPGLanguageNotSupported, DiscoveryRuleError, DiscoveryRuleParsingResultError, InvalidSastTools
from core.measurement import Measurement
from core.discovery_evaluation import evaluate_discovery_rule_results, DiscoveryResult

from core.instance import Instance
from core.pattern import Pattern

# mand_finding_joern_keys = ["filename", "methodFullNa
mand_finding_joern_keys = ["filename", "lineNumber"]



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


def run_joern_discovery_rule(cpg: Path, discovery_rule: Path) -> Dict:
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
        return joern_output
    except subprocess.CalledProcessError as e:
        ee = DiscoveryRuleError(
            "Failed in either executing the joern discovery rule or fetching its raw output" + utils.get_exception_message(
                e))
        logger.exception(ee)
        raise ee


def patch_PHP_discovery_rule(discovery_rule: Path, language: str, output_dir):
    if language.upper() != "PHP":
        return discovery_rule
    t_str = ".location.toJson);"
    p_str = ".repeat(_.astParent)(_.until(_.filter(x => x.lineNumber.getOrElse(-1) != -1))).location.toJson);"
    with open(discovery_rule) as ifile:
        # TODO: to be continued
        lines = ifile.readlines()
    newlines = []
    changed = False
    for l in lines:
        newl = l.replace(t_str, p_str) if re.match('\s*val x[\d_]+ = \(name, "[^"]+", cpg\.call.*(\.location\.toJson)\);\s*', l) else l
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


def discovery(src_dir: Path, l_tp_id: list[int], tp_lib_path: Path, itools: list[Dict],
              language: str,
              build_name: str,
              disc_output_dir: Path,
              timeout_sec: int = 0,
              ignore=False,
              cpg: str = None) -> Dict:
    logger.info("Discovery for patterns started...")
    # TODO: to support multiple discovery methods the following would need major refactoring.
    # - CPG is specific to Joern
    # - each discovery rule tells which method to use
    # - on the other hand you do not want to compute the CPG multiple times

    # if a CPG name is specified, expect it in TARGET_DIR. Else, generate new CPG from source
    if cpg is not None:
        cpg_path: Path = src_dir / cpg
        if not cpg_path.exists():
            logger.error(f"The specified CPG file {cpg_path} does not exist...")
            raise FileNotFoundError
    else:
        cpg_path: Path = generate_cpg(src_dir, language, build_name, disc_output_dir, timeout_sec=timeout_sec)
    return _run_discovery(cpg_path, l_tp_id, tp_lib_path, language, build_name, disc_output_dir, itools, ignore, timeout_sec)


def _run_discovery(cpg: Path, l_tp_id: list[int], tp_lib: Path,
                    language: str,
                    build_name: str,
                    disc_output_dir: Path,
                    itools: list[Dict] = [],
                    ignored: bool = False,
                    timeout_sec: int = 0) -> Dict:
    # preprocessing
    valid_instances, invalid_instances = _get_discovery_valid_instances(l_tp_id, language, tp_lib)
    supported_by_sast = []
    no_meas_result = []
    sast_measurements = None
    if not ignored:
        # TODO: the sast dict, where there is written for each instance what the measurement status is
        output = _preprocess_for_discovery_under_measurement(valid_instances, itools, tp_lib, language)
        valid_instances, no_meas_result, supported_by_sast = output
        sast_measurements = _get_sast_measurements(invalid_instances, valid_instances, no_meas_result, supported_by_sast)
        print(sast_measurements)
    grouped_instances = _group_by_discovery_method(valid_instances)

    # discovery
    discovery_method_not_supported_instances = []
    for discovery_method, instances in grouped_instances.items():
        if discovery_method == "joern":
            # generate one rule in order to save loading the cpg for each rule
            dr_path, parsing_error_instances, rule_id_instance_mapping = _get_large_discovery_rule(instances, disc_output_dir, build_name)
            # execute joern discovery
            pdr = patch_PHP_discovery_rule(dr_path, language, output_dir=disc_output_dir)
            findings = run_joern_discovery_rule(cpg, pdr)
        else:
            discovery_method_not_supported_instances += instances
    
    # evaluate
    invalid_instances = {
        "invalid discovery rule": invalid_instances, 
        "error while parsing discovery rule": parsing_error_instances,
        "discovery method not supported": discovery_method_not_supported_instances,
        "supported by SAST": supported_by_sast,
        "no meas result": no_meas_result
        }
    # At the moment, this only works for joern
    return evaluate_discovery_rule_results(findings, rule_id_instance_mapping, invalid_instances, 
                                    "joern", disc_output_dir, build_name, pdr, sast_measurements)


def _get_discovery_valid_instances(list_of_tp_ids: list, language: str, tp_lib: Path):
    logger.info("Validating discovery rules for instances started.")
    valid_instances = []
    invalid_instances = []
    for tp_id in list_of_tp_ids:
        target_pattern = Pattern.init_from_id_and_language(tp_id, language, tp_lib)
        for instance in target_pattern.instances:
            is_valid = instance.validate_for_discovery()
            if is_valid:
                valid_instances += [instance]
            else:
                logger.warning(f"Could not find correct rule for instance ({instance}). You might want to write/repair this rule.")
                invalid_instances += [instance]
    logger.info("Validating discovery rules for instances finished.")
    return valid_instances, invalid_instances


def _get_instance_measurement_mapping(meas_lang_dir):
    # WARNING: This code heavily relies on the structure of `measurements`
    # collect the paths of the measurement results for every instance in a dict of form {<pattern_id>_i<instance_id>}
    all_meas_res_for_pat = utils.list_directories(meas_lang_dir)
    instance_meas_res_mapping = {}
    for meas_dir_pat in all_meas_res_for_pat:
        pattern_id = utils.get_id_from_name(meas_dir_pat.name)
        instance_dirs = utils.list_directories(meas_dir_pat)
        for instance_meas_dir in instance_dirs:
            instance_id = utils.get_id_from_name(instance_meas_dir.name)
            meas_file = utils.get_last_measurement_for_pattern_instance(instance_meas_dir)
            key = f"{pattern_id}_i{instance_id}"
            instance_meas_res_mapping[key] = meas_file
    return instance_meas_res_mapping


def _get_large_discovery_rule(instances_to_include: list[Instance], out_dir: Path, build_name: str):
    # this function puts all rules of all instances into one single rule
    # each of the discovery rules will be assigned a sub_rule_id, that can be used to identify the results afterwards
    logger.info("Preparing discovery rule.")
    # prefix for the new rule
    all_lines = ['@main def main(name : String): Unit = {', '\timportCpg(name)']
    # init constants
    cannot_parse_rules = [] # all the instances, where there is an error, when trying to parse their rule into a large rule
    sub_rule_id_path_mapping = {} # mapping between the rule path and the assigned sub_rule_id
    sub_rule_id_instance_mapping = {} # mapping between the id, and the instances (could also use a mapping between rule path and all instances, that refere to the rule, ids, are a bit easier to handle in post processing)
    for instance in instances_to_include:
        dr = instance.discovery_rule
        if dr in sub_rule_id_path_mapping:
            # the discovery rule has already been appended to the new large rule
            sub_rule_id = sub_rule_id_path_mapping[dr]
            sub_rule_id_instance_mapping[sub_rule_id] += [instance]
            continue
        # get a uuid, be careful, when you have more than 2^14 rules, there might be duplicates
        sub_rule_id = str(uuid1())
        try:
            rule = _read_rule(dr)
            all_lines += _sanitize_rule(rule, f"{instance.pattern_id}_{instance.instance_id}", sub_rule_id)
        except Exception:
            # there was a problem parsing the rule
            cannot_parse_rules += [instance]
            logger.warning(f"The discovery rule for {instance} cannot be parsed, make sure the rule follows the template structure.")
            continue
        # update the mappings
        sub_rule_id_path_mapping[dr] = sub_rule_id
        sub_rule_id_instance_mapping[sub_rule_id] = [instance]
    # postfix for the new rule
    all_lines += ['\tdelete;', '}']
    # write the new rule into out, that the user can take a look at the rule
    new_dr_rule_path = out_dir / f"_discovery_rule_{build_name}.sc"
    with open(new_dr_rule_path, "w") as dr_file:
        dr_file.writelines("\n".join(all_lines))
    return new_dr_rule_path, cannot_parse_rules, sub_rule_id_instance_mapping


def _get_sast_measurements(invalid: list, valid: list, no_meas_result: list, supported: list) -> Dict:
    assert len(set(invalid + valid + no_meas_result + supported)) == len(invalid + valid + no_meas_result + supported)
    # all instances, where the instance does not validate for discovery
    invalid_mapping = {repr(i): "invalid" for i in invalid}
    # all instances, that will be used for discovery
    valid_mapping = {repr(i): "not_supported" for i in valid}
    # all instances, that do not have a measurment result
    no_meas_res_mapping = {repr(i): "not_found" for i in no_meas_result}
    # all instances, where the SAST tool was correct when measuring this instance
    supported_mapping = {repr(i): "supported" for i in supported} 
    return {**invalid_mapping, **valid_mapping, **no_meas_res_mapping, **supported_mapping}


def _group_by_discovery_method(list_of_discovery_valid_instances: list[Instance]) -> dict:
    grouped_instances = {}
    for instance in list_of_discovery_valid_instances:
        method = instance.discovery_method
        if method not in grouped_instances:
            grouped_instances[method] = []
        grouped_instances[method] += [instance]
    
    return grouped_instances


def _preprocess_for_discovery_under_measurement(list_of_instances: list,
                                                itools: list[Dict], 
                                                tp_lib: Path,
                                                language: str):
    # filter over tools
    tools = utils.filter_sast_tools(itools, language)
    if not tools:
        e = InvalidSastTools()
        logger.exception(e)
        raise e
    # Make end-user aware of the tools that do not support the targeted language and that thus will be ignored
    not_supported_tools = [t for t in itools if t not in tools]
    if not_supported_tools:
        logger.warning(
            f"Some of the tools do not support the {language} language: {not_supported_tools}. These tools will just be ignored for the discovery.")
    

    meas_lang_dir: Path = utils.get_measurement_dir_for_language(tp_lib, language)
    if not meas_lang_dir.is_dir():
        logger.warning(f"There is are no measurement results in {meas_lang_dir}")
        return [], list_of_instances, []
    # Get all measurement results for all instances
    instance_meas_res_mapping = _get_instance_measurement_mapping(meas_lang_dir)

    # filter instances
    instances_without_measurement_results = []
    instances_for_discovery = []
    instances_supported_by_sast = []
    instance: Instance
    for instance in list_of_instances:
        key = f"{instance.pattern_id}_i{instance.instance_id}"
        if key in instance_meas_res_mapping:
            # there is a measurement file for this particular instance
            l_last_meas = measurement.load_measurements(instance_meas_res_mapping[key], tp_lib, language)
            meas_tpi_by_tools: list[Measurement] = [meas for meas in l_last_meas if
                                                    measurement.any_tool_matching(meas, tools)]
            if not meas_tpi_by_tools:
                # there are measurement results, but there is no result for the tool(s) specified
                logger.warning(
                    f"No measurements of the tools specified ({[t['name'] + ':' + t['version'] for t in tools]}) for the instance {instance}.")
                instances_without_measurement_results += [instance]
                continue
            # at least one of the specified tools offers a measurement
            # discovery continue iff at least one tool not supporting the tpi
            is_supported = True
            for tool in tools:
                # does this instance have a measurement for this tool?
                meas_tpi_by_tool = [meas for meas in meas_tpi_by_tools if measurement.any_tool_matching(meas, [tool])]
                if not meas_tpi_by_tool:
                    logger.warning(
                        f"No measurements of tool {tool['name'] + ':' + tool['version']} for this instance {instance}. You may want to run that measurement...")
                    continue
                meas_tpi_not_supported_by_tool = [meas for meas in meas_tpi_by_tool if not meas.result]
                if meas_tpi_not_supported_by_tool:
                    logger.info(
                        f"Last measurement indicating that the tool {tool['name'] + ':' + tool['version']} does not support the pattern instance. Discovery rule will be run")
                    instances_for_discovery += [instance]
                    is_supported = False
                    break
            if is_supported:
                instances_supported_by_sast += [instance]
        else:
            # there is no measurement file for this instance
            instances_without_measurement_results += [instance]
    return instances_for_discovery, instances_without_measurement_results, instances_supported_by_sast


def _read_rule(rule_path: Path):
    with open(rule_path, 'r') as infile:
        res = infile.readlines()
    start = -1
    end = -1
    for idx, line in enumerate(res):
        if 'importCpg(name)' in line.strip():
            start = idx
        elif 'delete;' in line.strip():
            end = idx
    return res[start+1:end]


def _sanitize_rule(raw_lines: list, suffix: str, sub_rule_id: str):
    # get all variable_names, that need replacing, as in one big rule, variable names could be double
    # we add a certain unique suffix to each variable
    variables_to_replace  = []
    for l in raw_lines:
        if 'val ' in l or 'def ' in l:
            variables_to_replace += [l.split(' = ')[0].replace('val ', '').replace('def ', '').lstrip()]
    new_lines = [f'\tprint("{sub_rule_id}: ")']
    for l in raw_lines:
        line = l
        for v in variables_to_replace:
            line = line.replace(v, f'{v}_{suffix}')
        new_lines += [line.rstrip()]
    return new_lines


def get_ignored_tp_from_results(d_res: list[DiscoveryResult]):
    results_to_consider = filter(lambda res: any(map(lambda v: v in res.sast_measurement, ["not_found"])), d_res)
    return sorted(list(set([f"{i.pattern_id}" for res in results_to_consider for i in res.instances])))


def get_ignored_tpi_from_results(d_res, ignored_as):
    return sorted(list(set([repr(i) for res in filter(lambda r: ignored_as in r.sast_measurement, d_res) for i in res.instances])))


def get_error_tpi_from_results(d_res):
    return sorted(list(set([repr(i) for res in filter(lambda r: r.status == "ERROR_DISCOVERY", d_res) for i in res.instances])))


def get_unsuccessful_discovery_tpi_from_results(d_res):
    return sorted(list(set([repr(i) for res in filter(lambda r: r.status == "ERROR_DISCOVERY", d_res) for i in res.instances])))


def get_successful_discovery_tpi_from_results(d_res):
    return sorted(list(set([
        repr(i) for res in filter(lambda r: r.status == "DISCOVERY" or r.status == "NO_DISCOVERY", d_res) 
        for i in res.instances])))


def get_num_discovery_findings_from_results(d_res):
    return len(list([repr(i) for res in filter(lambda r: r.status == "DISCOVERY", d_res) for i in res.instances]))


############################################################################
# TODO: make manual discovert and checkdiscovery work again

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
            all_findings = run_joern_discovery_rule(cpg, patched_discovery_rule)
            logger.info("Parsing the results of specific discovery rules started...")
            for query_name, findings_for_rule in all_findings.items():
                if len(findings_for_rule) == 0:
                    findings.append({
                        "filename": None,
                        "methodFullName": None,
                        "lineNumber": None,
                        "queryName": query_name,
                        "queryFile": str(discovery_rule),
                        "result": discovery_result_strings["no_discovery"]
                    })
                for f in findings_for_rule:
                    if any(k not in f for k in mand_finding_joern_keys):
                        error = f"Discovery - finding {f} does not include some mandatory keys ({mand_finding_joern_keys}). Please fix the rule and re-run. Often this amount to use `location.toJson`"
                        logger.error(error)
                        continue
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
