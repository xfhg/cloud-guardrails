from typing import Dict
import os
import json
from operator import itemgetter
from tabulate import tabulate

COMPLIANCE_DATA_FILE = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "data",
    "results.json"
))
with open(COMPLIANCE_DATA_FILE) as json_file:
    COMPLIANCE_DATA = json.load(json_file)


class BenchmarkEntry:
    def __init__(self, benchmark: str, category: str, requirement: str, requirement_id: str):
        self.benchmark = benchmark
        self.category = category
        self.requirement = requirement
        self.requirement_id = requirement_id

    def __repr__(self):
        result = dict(
            benchmark=self.benchmark,
            category=self.category,
            requirement=self.requirement,
            requirement_id=self.requirement_id,
        )
        return json.dumps(result)

    def __str__(self):
        return json.dumps(self.__repr__())

    def json(self) -> dict:
        return json.loads(self.__repr__())


class PolicyDefinitionMetadata:
    def __init__(self, policy_id: str, service_name: str, effects: str, description: str, name: str, benchmark: str,
                 category: str, requirement: str, requirement_id: str, github_link: str, github_version: str):
        self.policy_id = policy_id
        self.service_name = service_name
        self.effects = effects
        self.description = description
        self.name = name
        self.github_link = github_link
        self.github_version = github_version
        self.benchmarks = self._benchmarks(benchmark=benchmark, requirement=requirement, requirement_id=requirement_id, category=category)

    def __repr__(self) -> str:
        benchmark_response = {}
        for benchmark, benchmark_value in self.benchmarks.items():
            benchmark_response[benchmark_value.benchmark] = benchmark_value.json()
        result = dict(
            policy_id=self.policy_id,
            effects=self.effects,
            description=self.description,
            name=self.name,
            service_name=self.service_name,
            github_link=self.github_link,
            github_version=self.github_version,
            benchmarks=benchmark_response,
        )
        return json.dumps(result)

    def __str__(self):
        return self.__repr__()

    def json(self) -> dict:
        return json.loads(self.__repr__())

    def _benchmarks(self, benchmark: str, category: str, requirement: str, requirement_id: str) -> {BenchmarkEntry}:
        result = {}
        benchmark_entry = BenchmarkEntry(benchmark=benchmark, category=category, requirement=requirement, requirement_id=requirement_id)
        result[benchmark] = benchmark_entry
        return result

    def get_compliance_data_matching_policy_definition(self) -> dict:
        result = {}
        for benchmark, benchmark_value in self.benchmarks.items():
            benchmark_name = benchmark_value.benchmark
            benchmark_string = f"{benchmark_value.benchmark}: {benchmark_value.requirement_id}"
            # benchmark_string = f"{benchmark_value.benchmark}: {benchmark_value.requirement_id} ({benchmark_value.requirement})"
            result[benchmark_name] = benchmark_string
        return result


class ComplianceResultsTransformer:
    """
    Transforms the metadata generated from scraping into the JSON format that is friendlier for our analysis.

    See the ComplianceData class to actually use this data.
    """
    def __init__(self, results_list: list):
        self.results_list_json = results_list
        self.results = self._results()

    def __repr__(self) -> str:
        response = {}
        for result_key, result_value in self.results.items():
            response[result_key] = result_value.json()
        return json.dumps(response)

    def json(self) -> dict:
        return json.loads(self.__repr__())

    def __str__(self):
        return self.__repr__()

    def _results(self) -> {PolicyDefinitionMetadata}:
        results = {}
        for result in self.results_list_json:
            if result.get("name") not in results.keys():
                policy_definition_metadata = PolicyDefinitionMetadata(
                    policy_id=result.get("policy_id"),
                    service_name=result.get("service_name"),
                    effects=result.get("effects"),
                    description=result.get("description"),
                    name=result.get("name"),
                    benchmark=result.get("benchmark"),
                    category=result.get("category"),
                    requirement=result.get("requirement"),
                    requirement_id=result.get("requirement_id"),
                    github_link=result.get("github_link"),
                    github_version=result.get("github_version"),
                )
                results[result.get("name")] = policy_definition_metadata
            else:
                benchmark = result.get("benchmark")
                category = result.get("category")
                requirement = result.get("requirement")
                requirement_id = result.get("requirement_id")
                benchmark_entry = BenchmarkEntry(benchmark=benchmark, category=category, requirement=requirement,
                                                 requirement_id=requirement_id)
                results[result.get("name")].benchmarks[benchmark] = benchmark_entry
        return results


class PolicyComplianceData:
    def __init__(self):
        self.compliance_data = COMPLIANCE_DATA
        self.policy_definition_metadata = self._policy_definition_metadata()

    def __repr__(self):
        return json.dumps(COMPLIANCE_DATA)

    def __str__(self):
        return json.dumps(COMPLIANCE_DATA)

    def json(self):
        return COMPLIANCE_DATA

    def _policy_definition_metadata(self) -> {PolicyDefinitionMetadata}:
        results = {}
        for metadata_key, metadata_values in self.compliance_data.items():
            name = metadata_values.get("name")
            policy_id = metadata_values.get("policy_id")
            service_name = metadata_values.get("service_name")
            effects = metadata_values.get("effects")
            description = metadata_values.get("description")
            github_link = metadata_values.get("github_link")
            github_version = metadata_values.get("github_version")
            for benchmark_key, benchmark_values in metadata_values.get("benchmarks").items():
                benchmark = benchmark_key
                category = benchmark_values.get("category")
                requirement = benchmark_values.get("requirement")
                requirement_id = benchmark_values.get("requirement_id")
                policy_definition_metadata = PolicyDefinitionMetadata(
                    policy_id=policy_id,
                    service_name=service_name,
                    effects=effects,
                    description=description,
                    name=name,
                    benchmark=benchmark,
                    category=category,
                    requirement=requirement,
                    requirement_id=requirement_id,
                    github_link=github_link,
                    github_version=github_version,
                )
                if not results.get(name, None):
                    results[name] = {}
                    results[name][benchmark] = policy_definition_metadata
                else:
                    results[name][benchmark] = policy_definition_metadata
        return results

    def policy_definition_names(self):
        result = list(self.policy_definition_metadata.keys())
        result.sort()
        return result

    def get_benchmark_data_matching_policy_definition(self, policy_definition_name: str) -> dict:
        results = {}
        metadata = self.policy_definition_metadata.get(policy_definition_name)
        for benchmark in metadata:
            results[benchmark] = metadata[benchmark].get_compliance_data_matching_policy_definition()
        return results


class ComplianceCoverage:
    def __init__(self, display_names: list):
        self.provided_display_names = display_names
        self.policy_compliance_data = PolicyComplianceData()
        self.matching_metadata = self._matching_metadata()

    def _matching_metadata(self) -> dict:
        results = {}
        policy_definition_names = self.policy_compliance_data.policy_definition_names()
        for display_name in self.provided_display_names:
            # Trim [Preview]:
            name = display_name.replace("[Preview]: ", "")
            if name in policy_definition_names:
                benchmark_data = self.policy_compliance_data.get_benchmark_data_matching_policy_definition(name)
                results[display_name] = benchmark_data
        return results

    def markdown_table(self) -> str:
        headers = ["Service", "Policy Definition", "Benchmarks"]
        results = []
        for policy_definition_name in self.matching_metadata:
            name = policy_definition_name.replace("[Preview]: ", "")
            benchmark_strings = []
            for benchmark in self.matching_metadata[policy_definition_name]:
                service_name = self.policy_compliance_data.policy_definition_metadata[name][benchmark].service_name
                github_link = self.policy_compliance_data.policy_definition_metadata[name][benchmark].github_link
                benchmark_strings.append(self.matching_metadata[policy_definition_name][benchmark][benchmark])
                policy_definition_string = f"[{policy_definition_name}]({github_link})"
            results.append([service_name, policy_definition_string, "<br>".join(benchmark_strings)])
        results = sorted(results, key=itemgetter(0, 1, 2))
        return tabulate(results, headers=headers, tablefmt="github")
