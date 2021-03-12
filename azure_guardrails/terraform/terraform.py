import os
import json
import logging
from jinja2 import Template, Environment, FileSystemLoader
from azure_guardrails.shared import utils
logger = logging.getLogger(__name__)


def get_terraform_template(policy_names: dict, subscription_name: str = "",
                           management_group: str = "", enforcement_mode: bool = False) -> str:
    if subscription_name == "" and management_group == "":
        raise Exception("Please supply a value for the subscription name or the management group")
    if enforcement_mode:
        enforcement_string = "true"
    else:
        enforcement_string = "false"
    # TODO: Shorten the subscription name if it is over X characters
    if subscription_name:
        name = f"{subscription_name}-noparams"
    # TODO: Shorten the management group name if it is over X characters
    else:
        name = f"{management_group}-noparams"
    name = name.replace("-", "_")
    name = name.lower()
    template_contents = dict(
        name=name,
        policy_names=policy_names,
        subscription_name=subscription_name,
        management_group=management_group,
        enforcement_mode=enforcement_string,
    )
    template_path = os.path.join(os.path.dirname(__file__), "no-parameters")
    env = Environment(loader=FileSystemLoader(template_path))  # nosec
    template = env.get_template("policy-set-with-builtins-v2.tf")
    return template.render(t=template_contents)


class TerraformTemplate:
    """Terraform Template with Parameters"""

    def __init__(self,
                 parameters: dict,
                 subscription_name: str = "",
                 management_group: str = "", enforcement_mode: bool = False):
        # TODO: Shorten the subscription name if it is over X characters
        if subscription_name:
            self.name = f"{subscription_name}-params"
        # TODO: Shorten the management group name if it is over X characters
        else:
            self.name = f"{management_group}-params"
        # self.name = name
        self.service_parameters = self._parameters(parameters)

        if subscription_name == "" and management_group == "":
            raise Exception("Please supply a value for the subscription name or the management group")
        self.subscription_name = subscription_name
        self.management_group = management_group
        if enforcement_mode:
            self.enforcement_string = "true"
        else:
            self.enforcement_string = "false"

    def _parameters(self, parameters) -> dict:
        """Separated this out just in case we need to do more processing"""
        results = {}
        for service_name, policy in parameters.items():
            for display_name, parameters in policy.items():
                # This will allow us to avoid duplicate parameters
                parameter_details = {display_name: parameters}
                if service_name in results:
                    results[service_name].update(parameter_details)
                else:
                    results[service_name] = parameter_details
                # if display_name not in results.get(service_name):
        return results

    def get_policy_parameters(self, service_name, policy_name):
        return self.service_parameters.get(service_name).get(policy_name)

    def policy_names(self) -> list:
        result = []
        for service, policies_with_params in self.service_parameters.items():
            result.extend(list(policies_with_params.keys()))
        return result

    def all_parameters(self) -> dict:
        result = {}
        for service, policies_with_params in self.service_parameters.items():
            for policy, parameters in policies_with_params.items():
                for parameter in parameters:
                    result[parameter] = parameters[parameter]
        return result

    def policy_definition_reference_parameters(self) -> dict:
        result = {}
        for service, policies_with_params in self.service_parameters.items():
            for key in policies_with_params:
                parameter_names = list(policies_with_params[key].keys())
                result[key] = parameter_names
        return result

    def rendered(self) -> str:
        all_parameters = json.dumps(self.all_parameters(), indent=4)
        template_contents = dict(
            name=self.name,
            policy_definition_reference_parameters=self.policy_definition_reference_parameters(),
            all_parameters=all_parameters,
            sorted_policies=self.service_parameters,
            subscription_name=self.subscription_name,
            management_group=self.management_group,
            enforcement_mode=self.enforcement_string,
        )
        template_path = os.path.join(os.path.dirname(__file__), "parameters")
        env = Environment(loader=FileSystemLoader(template_path))  # nosec
        env.filters['debug'] = print
        template = env.get_template("policy-set-with-parameters.tf")
        result = template.render(t=template_contents)
        return result
