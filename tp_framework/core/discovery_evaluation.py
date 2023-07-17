import json
import re
from copy import deepcopy
from typing import Dict, Tuple
from pathlib import Path

import config
from core import utils
import logging
from core import loggermgr

logger = logging.getLogger(loggermgr.logger_name(__name__))

mand_finding_joern_keys = ["filename", "lineNumber"]

discovery_result_strings = {
    "no_discovery": "NO_DISCOVERY",
    "discovery": "DISCOVERY",
    "error": "ERROR_DISCOVERY",
    "supported": "SUPPORTED_BY_SAST"
}

class DiscoveryResult:
    def __init__(self, rule_name: str, 
                 instances: list, 
                 cpg_path: str, 
                 result: list[Dict],
                 rule_id: str, 
                 query_file: str = None) -> None:
        self.cpg_path = cpg_path.strip()
        self.instances = instances
        self.result = result
        self.rule_name = rule_name.strip()
        self.rule_id = rule_id.strip()
        self.queryFile = query_file

        self.error = None
        self.status = None

    def to_csv(self) -> list:
        # patternId,instanceId,instanceName,sast_measurement,method,queryFile,queryHash,queryName,queryAccuracy,queryAlreadyExecuted,discovery,filename,lineNumber,methodFullName
        res = []
        assert isinstance(self.result, dict) or self.result is None
        for idx, instance in enumerate(self.instances):
            res += [{
                "patternId": instance.pattern_id,
                "instanceId": instance.instance_id, 
                "instanceName": instance.name, 
                "sast_measurement": self.sast_measurement[idx],
                "method": instance.discovery_method,
                "queryFile": str(self.queryFile), 
                "queryHash": utils.get_file_hash(self.queryFile) if self.queryFile else "",
                "queryName": self.rule_name, 
                "queryAccuracy": instance.discovery_rule_accuracy,
                "queryAlreadyExecuted": not bool(self.error) and idx != 0, 
                "discovery": bool(self.result) if not self.error else "failure", 
                "filename": self.result["filename"] if self.result else None, 
                "lineNumber": self.result["lineNumber"] if self.result else None,
                "methodFullName": self.result["methodFullName"] if self.result and "methodFullName" in self.result else None
            }]
        return res

    def to_json(self) -> dict:
        # discovery, filename, lineNumber, methodFullName, queryFile, queryName
        return {
            "discovery": bool(self.result),
            "filename": self.result["filename"],
            "lineNumber": self.result["lineNumber"],
            "methodFullName": self.result["methodFullName"] if "methodFullName" in self.result else None,
            "queryFile": str(self.queryFile),
            "queryName": self.rule_name
        }

    def __str__(self) -> str:
        return f"{self.instances}_{len(self.result)}"


def evaluate_discovery_rule_results(raw_findings: str, 
                                    rule_id_instance_mapping: dict, 
                                    invalid_instances: dict,
                                    discovery_method: str,
                                    output_dir: Path,
                                    build_name: str,
                                    query_file: Path,
                                    sast_measurement: dict = None) -> list[DiscoveryResult]:
    # parse raw findings into DiscoveryResults
    findings = _process_raw_findings(raw_findings, rule_id_instance_mapping, query_file)

    # process raw results according to discovery method
    if discovery_method == "joern":
        positive_res, error_instances = _process_joern_results(findings)
        invalid_instances["joern output error"] = error_instances
    else:
        logger.error("Discovery method not yet supported")

    # figure out, which results are missing
    misssing_instances = _process_missing_instances(positive_res, rule_id_instance_mapping)
    invalid_instances["parsing error"] = misssing_instances

    # process error results
    negative_res = _process_negative_instances(invalid_instances)

    # add measurement
    all_res = positive_res + negative_res
    all_res = _add_measurement(all_res, sast_measurement)
    # export results
    _export_csv_file(sorted(all_res, key=lambda x: x.rule_name), output_dir, build_name)
    _export_findings_file(positive_res, output_dir, build_name)
    return all_res


def _parse_finding_line(raw_finding_line: str, rule_id_instance_mapping: dict, query_file: Path):
    # <rule_id>: (<path_to_cpg_used>, <rule_name>, <results as JSON>)\n
    raw_finding_line = raw_finding_line.strip()
    # get rule_id
    rule_id = raw_finding_line.split(":")[0]
    # get the actual result tuple
    tuple_result = raw_finding_line[len(rule_id)+1:].strip()
    tuple_result = tuple_result[1:-1] # remove ()
    splitted_results = tuple_result.split(",")
    # extract cpg_path, rule_name and result from tuple
    cpg_path = splitted_results[0]
    rule_name = splitted_results[1]
    result = tuple_result[len(cpg_path)+len(rule_name)+2:]
    # load it as json
    result_list = json.loads(result)
    instances = rule_id_instance_mapping[rule_id.strip()]

    # return a discovery_result
    return DiscoveryResult(rule_name, instances, cpg_path, result_list, rule_id, query_file=query_file)


def _process_raw_findings(raw_findings: str, rule_id_instance_mapping: dict, query_file: Path) -> list[DiscoveryResult]:
    # raw findings are exepcted to be in the following format
    # <rule_id>: (<path_to_cpg_used>, <rule_name>, <results_as_list_of_JSON>)\n
    all_findings = raw_findings.strip().split("\n")
    d_results = []
    for finding in all_findings:
        if not re.match(r"^[^:]+: \(.*\)$", finding):
            logger.info(f"\033[92mSkipping line {finding} in output, does not meet the required format.\033[0m")
        try:
            d_results += [_parse_finding_line(finding, rule_id_instance_mapping, query_file)]
        except json.JSONDecodeError:
            logger.error(f"Could not parse result {finding}. The JSON result is corrupt.")
        except IndexError:
            logger.error(f"Could not parse '{finding}'. The result should be of the form (<path_to_cpg_used>, <rule_name>, <results_as_list_of_JSON>)\\n")
        except:
            logger.error(f"Something went wrong by parsing this line '{finding}'. Skipping...")
    logger.info("Discovery - rule execution done and raw output parsed.")
    return d_results


def _process_joern_results(list_of_discovery_results: list):
    error_instances = []
    all_findings = []
    d_result: DiscoveryResult
    for d_result in list_of_discovery_results:
        json_result = d_result.result
        if not json_result:
            d_result.result = None
            d_result.status = discovery_result_strings["no_discovery"]
            all_findings += [d_result]
            continue
        for finding in json_result:
            if any(k not in finding for k in mand_finding_joern_keys):
                error = f"Discovery - finding {finding} does not include some mandatory keys ({mand_finding_joern_keys}). Please fix the rule {d_result.rule_name} and re-run. Often this amount to use `location.toJson`"
                logger.error(error)
                error_instances += d_result.instances
                continue
            finding_result = deepcopy(d_result)
            finding_result.result = finding
            finding_result.status = discovery_result_strings["discovery"]
            all_findings += [finding_result]
    return all_findings, error_instances


def _add_measurement(result_list: list, sast_measurement: dict or None):
    res = []
    d_res: DiscoveryResult
    for d_res in result_list:
        d_res.sast_measurement = []
        if not sast_measurement:
            d_res.sast_measurement = ["ignored"] * len(d_res.instances)
        else:
            for instance in d_res.instances:
                d_res.sast_measurement += [sast_measurement[repr(instance)]]
        res += [d_res]
    return res


def _process_missing_instances(all_positive_results: list, rule_id_instance_mapping: dict):
    # The rule_id_instance_mapping should contain all instances whose discovery rule is included in the large discovery rule.
    # An instance could go missing, for example in _process_raw_findings, as we cannot tell, which instances the failing line affected
    # This function aims to collect all instances, that are in the rule_id_instance_mapping but not in the positive results
    missing_instances = []
    for rule_id, instances in rule_id_instance_mapping.items():
        res_with_this_id = list(filter(lambda res: res.rule_id == rule_id, all_positive_results))
        if not res_with_this_id:
            missing_instances += instances
    return missing_instances


def _process_negative_instances(dict_error_instances: dict):
    d_res = []
    for error, instances in dict_error_instances.items():
        if not instances:
            continue
        result = DiscoveryResult("", instances, "", None, "")
        result.status = discovery_result_strings["supported"] if "supported" in error else discovery_result_strings["error"]
        result.error = error
        d_res += [result]
    return d_res


def _export_findings_file(list_of_results: list, disc_output_dir: Path, build_name: str):
    findings = []
    d_res: DiscoveryResult
    for d_res in list_of_results:
        if d_res.status == "DISCOVERY":
            findings += [d_res.to_json()]
    ofile_csv = disc_output_dir / f"findings_{build_name}.json"
    with open(ofile_csv, "w") as json_file:
        json.dump(findings, json_file, sort_keys=True, indent=4)


def _export_csv_file(list_of_results: list, disc_output_dir: Path, build_name: str):
    rows = []
    d_res: DiscoveryResult
    for d_res in list_of_results:
        rows += d_res.to_csv()
    rows = sorted(rows, key=lambda d: (d["patternId"], d["instanceId"]))
    ofile_csv = disc_output_dir / f"discovery_{build_name}.csv"
    utils.write_csv_file(ofile_csv, rows[0].keys(), rows)
