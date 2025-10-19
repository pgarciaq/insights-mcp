"""Red Hat Lightspeed cost management MCP Server.

MCP server for cost management via Red Hat Lightspeed API.
Provides cost analysis, showback, chargeback and resource optimization recommendations.
"""

import uuid
import logging
from enum import Enum
from typing import Any
import json

from insights_mcp.mcp import InsightsMCP

mcp = InsightsMCP(
    name="Lightspeed cost management MCP Server",
    toolset_name="costmanagement",
    api_path="api/cost-management/v1",
    instructions="""
    You are a helpful assistant that can help with cost management, showback and chargeback 
    on Red Hat OpenShift clusters, Amazon Web Services (AWS) cloud, Microsoft Azure cloud 
    and Google Cloud Platform (GCP). You will be consuming data from the Red Hat Lightspeed API, 
    specifically from the Cost Management API endpoints.
    
    You know that Red Hat OpenShift can on on premise or on the cloud. You know about OpenShift cloud services:
    Red Hat OpenShift on AWS (ROSA) clusters, Azure Red Hat OpenShift (ARO) clusters, and OpenShift Dedicated 
    (OSD) clusters on GCP.

    You know that an OpenShift cluster may be referred to by OpenShift integration name or by cluster UUID.

    You know that an AWS account may be referred to by AWS integration name, account name or account number.

    You know how to provide information about costs at the OpenShift entity name: cluster, node,
    namespace (also called "project" in OpenShift) and tag level (where "tags" in Cost Management include both 
    OpenShift labels and cloud provider tags).

    You know that setting up Cost Management involves at least the follow steps:
    - Read the customer cloud bill from a cloud (AWS, Azure, GCP) integration. Multiple cloud providers can be 
      integrated with Cost Management.
    - Read the customer OpenShift usage and capacity data from the Cost Management Metrics Operator (CMMO) data 
      payload that is sent to the Red Hat Hybrid Cloud Console. This data is gathered by the CMMO by scraping the 
      Prometheus instance that's running on that specific cluster. The Cost Management Metrics Operator must be 
      installed on every OpenShift cluster and an OpenShift integration must be created to associate the cluster 
      UUID with the cluster data payload.

    You know that the way Cost Management allocates a plurarity of costs coming from a cloud provider integration 
    into an OpenShift cluster is:
    - Read the rows in the cloud provider bill (cost report) and look for the resource identifiers, labels, IP 
      addresses, etc for the nodes (cloud instances).
    - Associate those costs to an OpenShift cluster by looking at the resource identifiers, labels, node names, 
      cluster names, etc in the OpenShift data.

    You know that Cost Management has a concept of "cost models" that may be used to add additional costs to be 
    allocated, or to modify the cost allocation rules. User may create cost models at the cloud provider (AWS, 
    Azure or GCP) level and at the OpenShift cluster level. A cost model is a set of rules that determine how costs 
    are allocated to OpenShift and/or cloud provider resources. There are different capabilities depending on the 
    cost model type:
    - Cloud provider (AWS, Azure or GCP) cost model: allows to add a markup or discount to a cloud integration, 
      therefore to all the costs flowing through that cloud integration. One cloud cost model may be associated 
      with multiple cloud integrations.
    - OpenShift cost model: allows to add a markup or discount to all the costs flowing through an OpenShift 
      cluster. Users may also create a price list with custom prices (rates) based on different metrics and 
      measurements:
      - Metric: cost per CPU core-hour.
        Measurement: per usage, per request or per effective usage (meaning the greatest of usage and request).
      - Metric: cost per GiB-hour of memory (RAM).
        Measurement: per usage, per request or per effective usage (meaning the greatest of usage and request).
      - Metric: cost per GiB-month of storage (disk).
        Measurement: per usage or per request.
      - Metric: per project cost. This cost could be used to represent a minimum cost per project, a service 
        level agreement (SLA) cost or alike.
        Measurement: per project per month.
      - Metric: cost per cluster.
        Measurement: per cluster per month, per cluster per hour or per cluster core per hour.
      - Metric: cost per node
        Measurement: per node per month, per node per hour or per node core per hour.
      - Metric: cost per persistent volume claim (PVC).
        Measurement: per PVC per month.
      - Metric: cost per virtual machine (VM).
        Measurement: cost per VM per month, cost per VM per hour, cost per VM core per month or cost per VM core per hour.
      User may define zero, one or more than one rates for each metric. Each rate shows as a different entry in the price list.
      Most costs at in the price list may be parameterize by using tag keys and values, from the tags that are
      enabled in Cost Management.
      One OpenShift cost model may be associated with multiple OpenShift clusters (OpenShift integrations).
    
    Regarding tags and labels:
    - You know that cloud tags are enabled by default in Cost Management.
    - You know that OpenShift labels are disabled by default in Cost Management and users must explicitly enable them. 
      Cost Management refers to OpenShift labels as "tags" too, same as cloud.
    - You know that multiple cloud provider tags and OpenShift labels may be combined ("mapped") by Cost Management users 
      into a single tag by using the tag mapping feature in Cost Management. OpenShift and the cloud provider will not know 
      about this mapping, though.
    - You know that both cloud tags and OpenShift labels may be used to parameterize the costs in the price list.
    - You know that Cost Management uses a combination of cloud tags and OpenShift labels to parameterize the costs in the 
      price list.

    You know that Cost Management calculates costs the right way:
    - It looks at exactly what node each pod or OpenShift VM was running at each moment in time
    - It looks at how much that node costs, including all the discounts, savings plans, etc
    - It does not use public prices
    - It does not use estimated costs
    - It does not use average costs from multiple nodes in the OpenShift cluster but rather the exact cost of the 
      node at the specific time period.

    You know that, after cost allocation by Cost Management, any cost related to an OpenShift entity has these components, displayed in the Cost Management web UI in a Sankey diagram:
    - Raw cost: cost coming directly from the cloud bill
    - Markup: positive or negative. It's a markup or discount to the raw cost, introduced either in the OpenShift cost model 
      or in the cloud cost model.
    - Usage cost: costs coming from rates defined in the price list in the OpenShift cost model.
    - Network unattributed cost
    - Storage unattributed cost
    - Worker unallocated cost

    In the OpenShift project detailed view:
    - Raw cost, markup and usage cost are aggregated by Cost Management to produce the total cost of the OpenShift project.
    - Network unattributed cost, storage unattributed cost and worker unallocated cost are aggregated by Cost Management to produce the overhead cost of running that OpenShift project.

    In the OpenShift cluster, node and tag detailed view: raw cost, markup and usage cost are aggregated by Cost Management to produce the total cost of the OpenShift cluster.

    You know that users may define cloud cost models, or OpenShift cost models, or both, or none. In case no cost model is defined, Cost Management will use the default ("implicit") strategy to allocate costs:
    - Take the cost of each OpenShift node, as computed earlier by associating a plurality of costs coming from a cloud integration and adding up any additional rates and markups or discounts defined in an AWS, Azure, GCP and/or OpenShift cost model.
    - Allocate cost to each pod based on the effective CPU usage of the pod.
    - Aggregate costs to the OpenShift namespace ("project") and cluster level.
    - Include overhead costs, as defined later, in the per-namespace and per-cluster cost allocation.

    You know that an OpenShift cluster (any Kubernetes cluster) has a control plane and a worker plane. You know that 
    users run their workloads in the worker place. You know that the control plane is not used to run workloads and Red Hat 
    does not charge a subscription fee for the control plane (but there's an associated infrastructure cost, either in the 
    cloud or on premise). You know that the worker plane is not fully utilized because users always leave some capacity unused 
    for future growth, or to accommodate unexpected workload spikes (eg. due to disaster recovery procedures migrating 
    workloads from a cluster to another one). Different users will leave different amounts of capacity unused, depending on 
    their business needs and their risk tolerance. But all of the capacity has to be paid for: either the customer (IT 
    department) pays for it, or the final user (typically, a line of business user) pays for it. By default, Cost Management 
    calculates the cost of the workload (pod/namespace) and then it calculates the "overhead cost of running OpenShift", ie:
    - Platform cost (cost of the control plane and any projects the user may have defined as "platform projects" in the 
      Settings in Cost Management.
    - Worker unallocated capacity cost (as reported by the "worker unallocated" project, which is a fake project that Cost 
      Management creates to represent the cost of the unallocated capacity in the worker plane).
    - Storage unattributed cost (as reported by the "storage unallocated" project, which is a fake project that Cost Management 
      creates to represent the cost of the unallocated storage in the cluster, eg. the cases where a Physical Volume is not 
      fully utilized because the PVC is smaller than the PV).
    - Network unattributed cost (as reported by the "network unallocated" project, which is a fake project that Cost Management 
      creates to represent the cost of the network traffic that is not attributed to a pod/namespace since as of today, 
      Cost Management does not have the ability to attribute network traffic to a pod/namespace, only to a node or cluster)

    You know that users may define "platform projects" in the Settings. There are two main reason for a project to be a 
    platform project:
    - It's part of the control plane, ie. projects with the "openshift-" or "kube-" prefix.
    - It's a cross-service that users provide to all the tenants using the same OpenShift cluster. These are typically single 
      sign-on (SSO) microservices, PDF generator microservices, security tools, monitoring tools, etc. Anything that is usually 
      used by all the tenants using the same OpenShift cluster should be a platform project.

    You know that in addition to costs, Cost Management also reports usage and capacity of the OpenShift cluster, OpenShift 
    node and OpenShift namespace (CPU usage in percentage, core-hours and maximum number of cores ever seen in the period; 
    memory usage in percentage, GiB-hours and maximum amount of memory ever seen in the period; storage usage in GiB; list of 
    PVCs and sizes).

    You know that if a customer has neither created a cloud cost model nor an OpenShift cost model with a price list, costs 
    will be zero but CPU, memory, etc usage will still be reported.

    You know that in addition to costs, Cost Management also provides rightsizing recommendations for containers running on 
    some namespace, node or cluster. These recommendations are based on the current usage and capacity data as gathered by the 
    Cost Management Metrics Operator from the Prometheus instance running on the cluster, and then considering three different 
    time periods (24 hours, 7 days and 15 days) and two profiles (optimize for cost or optimize for performance). Rightsizing 
    recommendations are only generated for containers running in OpenShift namespaces labeled with the tag key 
    'cost_management_optimizations' the tag value 'true', or the tag key 'insights_cost_management_optimizations' and the tag 
    value 'true'.

    You know that Cost Management has a 90 day retention policy for cost and usage data. If the user does not provide a specific
    time period, you should default to using the month-to-date data (ie. from the first day of the current month to the current day).

    [INSTRUCTION] When reporting a cost, always look for optimizations based on the past 7 days and show how many 
    recommendations are there for that namespace or cluster or node, and ask the user if they want to see the specifics. 
    Remember that rightsizing recommendations are only generated for containers running in OpenShift namespaces labeled with 
    cost_management_optimizations='true' or insights_cost_management_optimizations='true'. Always ask if they want to generate 
    an Ansible playbook to apply the optimized values. Always remind them to change the configuration in their GitOps 
    repository too, if they are using GitOps.

    Red Hat Lightspeed cost management requires correct RBAC permissions to be able to use the tools. Ensure that your
    Service Account has at least these roles: Cost Cloud viewer, Cost OpenShift viewer. If specific details about cost 
    models and/or price lists on AWS, Azure, GCP and/orOpenShift cost models will be needed, the following role will also 
    be needed: Cost Price List Viewer. If modifications to the AWS, Azure, GCP and/orOpenShift cost models will be needed, 
    the following role will also be needed: Cost Price List Administrator. If you don't have these roles, please contact your 
    organization administrator to get them.
    """,
)

mcp.logger = logging.getLogger("CostManagementMCP")


@mcp.tool(annotations={"readOnlyHint": True})
async def get_openapi() -> dict[str, Any] | str:
    """Get Red Hat Lightspeed cost management OpenAPI specification in JSON format."""
    return await mcp.insights_client.get("openapi.json")

# response["insights_url"] = f"{mcp.insights_client.insights_base_url}/{mcp.api_path}/reports/openshift/costs/?delta={delta}&filter[time_scope_units]={time_scope_units}&filter[time_scope_value]={time_scope_value}&filter[resolution]={resolution}&group_by[cluster]={id}&order_by={order_by}&offset={offset}&limit={limit}&start_date={start_date}&end_date={end_date}"
@mcp.tool(annotations={"readOnlyHint": True})
async def get_openshift_costs_by_cluster(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    delta_: str = "distributed_cost",
    filter_time_scope_units: str = "month",
    filter_time_scope_value: str = "-1",
    filter_resolution: str = "monthly",
    filter_cluster: str = "*",
    limit: int = 0,
    offset: int = 0,
    group_by: str = "cluster",
    order_by: str = "desc",
    start_date: str = "",
    end_date: str = "",
) -> dict[str, Any] | str:
    """Get cost per cluster for one or more clusters for a period of time (by default, month-to-date).

    This returns the cluster name, cluster UUID, cluster cost variation (month-to-month) and cluster cost.

    For more info refer to OpenAPI spec

    Args:
        delta_: whether to include the overhead cost of running OpenShift in the cost or not. "distributed_cost" includes the overhead cost, "cost" does not.
        filter_time_scope_units: time scope units. It can be "day" or "month".
        filter_time_scope_value: time scope value. When "time_scope_units" is "day", then "time_scope_value" may the "-10" (10 days back), "-30" (30 days back), etc. When "time_scope_units" is "month", then "time_scope_value" may be "-1" for month-to-date or "-2" for the previous month.
        filter_resolution: the resolution of the cost data. It can be "daily" or "monthly".
        filter_cluster: the cluster(s) to get the cost for. It can be a single cluster UUID, name or a wildcard ("*" means all clusters).
        limit: Pagination - Maximum number of records per page.
        offset: Pagination - Offset of first record of paginated response.
        group_by: the field to group the cost by. It can be "cluster", "project", "node" or "tag". For cluster costs, we will always group by "cluster".
        order_by: order based on the cluster cost ascending ("asc") or descending ("desc").
        start_date: the start date of the period to get the cost for. It must be in the format "YYYY-MM-DD". Optional - only included if non-empty.
        end_date: the end date of the period to get the cost for. It must be in the format "YYYY-MM-DD". Optional - only included if non-empty.
    """
    params = {
        "delta": delta_,
        "filter[time_scope_units]": filter_time_scope_units,
        "filter[time_scope_value]": filter_time_scope_value,
        "filter[resolution]": filter_resolution,
        "filter[cluster]": filter_cluster,
        "limit": limit,
        "offset": offset,
        "group_by[cluster]": group_by,
        "order_by": order_by,
    }
    
    # Only include start_date and end_date if they are non-empty
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    
    response = await mcp.insights_client.get(
        "reports/openshift/costs",
        params=params,
    )
    if isinstance(response, str):
        mcp.logger.info(f"Response: {json.dumps(response)}")
        return response

    if "data" not in response:
        return response

    return response

# @mcp.tool(annotations={"readOnlyHint": True})
# async def get_cve(cve: str, advisory_available: str = "true") -> dict[str, Any] | str:
#     """Get details about specific CVE.

#     This endpoint returns the CVE identification number, description, scores and other metadata.
#     The metadata includes the description, CVSS 2/3 Score, CVSS 2/3 attack vector, severity, public date,
#     modified date, business risk, status, a URL to Red Hat web pages, a list of advisories remediating
#     the CVE, and information regarding known exploits for the CVE.
#     For more info refer to OpenAPI spec

#     Args:
#         cve: CVE identifier. Example : CVE-2016-0800
#         advisory_available: String of booleans (array of booleans), where true shows CVE-system pairs
#                             with available advisory, false shows CVE-system pairs without available advisory.
#     """
#     response = await mcp.insights_client.get(
#         f"cves/{cve}",
#         params={"advisory_available": advisory_available},
#     )
#     if isinstance(response, str):
#         return response

#     if "data" not in response:
#         return response

#     response["data"]["url"] = f"{mcp.insights_client.insights_base_url}/insights/vulnerability/cves/{cve}"
#     advisories_list = []
#     for advisory in response["data"]["attributes"]["advisories_list"]:
#         advisories_list.append(f"https://access.redhat.com/errata/{advisory}")
#     response["data"]["attributes"]["advisories_list"] = advisories_list
#     return response


# @mcp.tool(annotations={"readOnlyHint": True})
# async def get_cve_systems(  # pylint: disable=too-many-arguments
#     cve: str,
#     *,
#     filter_: str = "",
#     limit: int = 10,
#     offset: int = 0,
#     sort: str = "-updated",
#     system_uuid: uuid.UUID | None = None,
# ) -> dict[str, Any] | str:
#     """Get list of systems affected by a given CVE.

#     This is a report of affected systems for a given CVE.
#     Use this tool to obtain list of all affected systems for a given CVE.
#     For more info refer to OpenAPI spec

#     Args:
#         cve: CVE identifier. Example : CVE-2016-0800 (Required)
#         filter_: Full text filter for the display name of system.
#         limit: Pagination - Maximum number of records per page.
#         offset: Pagination - Offset of first record of paginated response.
#         sort: Attribute sorting. Use `-` prefix to sort in descending order.
#         system_uuid: Filter based on Systems Inventory UUID.
#     """
#     response = await mcp.insights_client.get(
#         f"cves/{cve}/affected_systems",
#         params={
#             "filter": filter_,
#             "limit": limit,
#             "offset": offset,
#             "sort": sort,
#             "uuid": system_uuid,
#         },
#     )
#     if isinstance(response, str):
#         return response

#     if "data" not in response:
#         return response

#     for system in response["data"]:
#         system["url"] = f"{mcp.insights_client.insights_base_url}/insights/vulnerability/systems/{system['id']}"
#     response["insights_url"] = f"{mcp.insights_client.insights_base_url}/insights/vulnerability/cves/{cve}"
#     return response


# @mcp.tool(annotations={"readOnlyHint": True})
# async def get_system_cves(
#     system_uuid: uuid.UUID,
#     *,
#     filter_: str = "",
#     limit: int = 10,
#     offset: int = 0,
#     sort: str = "-public_date",
# ) -> dict[str, Any] | str:
#     """Get list of CVEs affecting a given system.

#     This is a report of CVEs affecting a given system.
#     Use this tool to obtain list of all CVEs affecting a given system.
#     For more info refer to OpenAPI spec

#     Args:
#         system_uuid: Systems Inventory UUID. Example : 123e4567-e89b-12d3-a456-426614174000 (Required)
#         filter_: Full text filter for the CVE name.
#         limit: Pagination - Maximum number of records per page.
#         offset: Pagination - Offset of first record of paginated response.
#         sort: Attribute sorting. Use `-` prefix to sort in descending order.
#     """
#     response = await mcp.insights_client.get(
#         f"systems/{system_uuid}/cves",
#         params={
#             "filter": filter_,
#             "limit": limit,
#             "offset": offset,
#             "sort": sort,
#         },
#     )
#     if isinstance(response, str):
#         return response

#     if "data" not in response:
#         return response

#     for cve in response["data"]:
#         cve["url"] = f"{mcp.insights_client.insights_base_url}/insights/vulnerability/cves/{cve['id']}"
#     response["insights_url"] = f"{mcp.insights_client.insights_base_url}/insights/vulnerability/systems/{system_uuid}"
#     return response


# @mcp.tool(annotations={"readOnlyHint": True})
# async def get_systems(  # pylint: disable=too-many-arguments,too-many-positional-arguments
#     filter_: str = "",
#     limit: int = 10,
#     offset: int = 0,
#     sort: str = "-updated",
#     group_names: str = "",
#     rhel_versions: str = "",
# ) -> dict[str, Any] | str:
#     """Get list of systems in Insights Vulnerability inventory.

#     List all systems registered in Insights Vulnerability service, including information about
#     their last check-in, system name, workspace name, RHEL version, and number of CVEs affecting them.
#     This tool shows both affected and not affected systems.
#     For more info refer to OpenAPI spec

#     Args:
#         filter_: Full text filter for the display name of system.
#         limit: Pagination - Maximum number of records per page.
#         offset: Pagination - Offset of first record of paginated response.
#         sort: Attribute sorting. Use `-` prefix to sort in descending order.
#         group_names: Filter based on workspace names. Comma separated list of workspace names.
#         rhel_versions: Filter based on RHEL versions. Comma separated list of RHEL versions.
#     """
#     params = {
#         "filter": filter_,
#         "limit": limit,
#         "offset": offset,
#         "sort": sort,
#     }
#     if group_names:
#         params["group_names"] = group_names
#     if rhel_versions:
#         params["rhel_versions"] = rhel_versions
#     response = await mcp.insights_client.get("systems", params=params)

#     if isinstance(response, str):
#         return response
#     if "data" not in response:
#         return response

#     for system in response["data"]:
#         system["url"] = f"{mcp.insights_client.insights_base_url}/insights/vulnerability/systems/{system['id']}"
#     response["insights_url"] = f"{mcp.insights_client.insights_base_url}/insights/vulnerability/systems"
#     return response


# # pylint: disable=too-many-locals
# @mcp.tool(annotations={"readOnlyHint": True})
# async def explain_cves(cves: list[str], system_uuid: uuid.UUID) -> dict[str, Any] | str:
#     """Explain why CVEs are affecting my environment.

#     This endpoint returns a detailed explanation of why CVEs are affecting my environment.
#     It uses VMAAS to explain the CVEs, what packages are affected and why.
#     Alongside with the information how this CVE can be fixed.
#     To get the explanation, we need to get the system UUID from the inventory and list of CVEs.
#     'affected_packages' in 'vmaas' response is a list of packages that are affected by the CVE.

#     To update affected packages, suggest to use Ansible Remediation Playbook via Remediations MCP tool.

#     Args:
#         cves: CVE identifiers. Example: CVE-2016-0800,CVE-2016-0801
#         system_uuid: System UUID. Example: 123e4567-e89b-12d3-a456-426614174000
#     """
#     explanations: dict[str, dict[str, Any]] = {
#         cve.upper(): {"details": {}, "is_affected": False, "rule": None, "reasons": []} for cve in cves
#     }

#     # get system profile from inventory
#     system_profile = await mcp.insights_client.client.make_request(
#         mcp.insights_client.client.get,
#         url=f"{mcp.insights_client.insights_base_url}/api/inventory/v1/hosts/{system_uuid}/system_profile",
#     )
#     if isinstance(system_profile, str) or "results" not in system_profile:
#         return system_profile

#     hosts = await mcp.insights_client.client.make_request(
#         mcp.insights_client.client.get,
#         url=f"{mcp.insights_client.insights_base_url}/api/inventory/v1/hosts/{system_uuid}",
#     )

#     if isinstance(hosts, str) or "results" not in hosts:
#         return hosts

#     system_name = hosts["results"][0]["display_name"]

#     for cve in cves:
#         # get cve details
#         cve_details = await mcp.insights_client.get(f"cves/{cve}")
#         explanations[cve]["details"] = cve_details
#         explanations[cve]["url"] = f"{mcp.insights_client.insights_base_url}/insights/vulnerability/cves/{cve}"

#         # check if system is affected by Security Rules
#         affected_systems = await mcp.insights_client.get(f"cves/{cve}/affected_systems?filter={system_name}")
#         if isinstance(affected_systems, str) or "data" not in affected_systems:
#             return affected_systems

#         if affected_systems["data"]:
#             if rule := affected_systems["data"][0].get("attributes", {}).get("rule"):
#                 explanations[cve]["is_affected"] = True
#                 explanations[cve]["rule"] = rule
#                 explanations[cve]["reasons"].append("CVE found using Security Rules.")

#     vmaas_json = _prepare_vmaas_request(system_profile)
#     vmaas_response = await mcp.insights_client.client.make_request(
#         mcp.insights_client.client.post,
#         url=f"{mcp.insights_client.insights_base_url}/api/vmaas/v3/vulnerabilities",
#         json=vmaas_json,
#     )

#     if isinstance(vmaas_response, str) or "cve_list" not in vmaas_response:
#         return vmaas_response

#     response_parts = [
#         ("cve_list", CVETypes.FIXABLE),
#         ("manually_fixable_cve_list", CVETypes.MANUALLY_FIXABLE),
#         ("unpatched_cve_list", CVETypes.UNFIXABLE),
#     ]
#     for response_part, cve_type in response_parts:
#         for item in vmaas_response[response_part]:
#             if item["cve"] in cves:
#                 _add_explanation(item["cve"], cve_type, item, explanations)

#     return explanations


# def _add_explanation(cve: str, type_: CVETypes, item: dict[str, Any], explanations: dict[str, dict[str, Any]]) -> None:
#     common_explanation = "There are packages affected by this CVE."
#     reasons = {
#         CVETypes.FIXABLE: f"{common_explanation} CVE can be fixed by applying the errata (advisories).",
#         CVETypes.MANUALLY_FIXABLE: f"{common_explanation} Manual steps are required to fix the CVE.",
#         CVETypes.UNFIXABLE: f"{common_explanation} CVE is not fixed by any errata (advisories).",
#         CVETypes.SECURITY_RULE: f"{common_explanation} CVE found using Security Rules.",
#     }

#     explanations[cve]["is_affected"] = True
#     if affected_packages := item.get("affected_packages"):
#         explanations[cve]["affected_packages"] = affected_packages
#     if errata := item.get("errata"):
#         explanations[cve]["errata"] = errata
#     if type_ == CVETypes.UNFIXABLE:
#         explanations[cve]["affected"] = item.get("affected")
#     if type_ == CVETypes.SECURITY_RULE:
#         explanations[cve]["rule"] = item.get("rule")
#     explanations[cve]["reasons"].append(reasons[type_])


# def _prepare_vmaas_request(system_profile: dict[str, Any]) -> dict[str, Any]:
#     """Prepare payload for VMAAS request."""
#     vmaas_json = {
#         "package_list": system_profile["results"][0]["system_profile"]["installed_packages"],
#         "repository_list": [
#             x["id"] for x in system_profile["results"][0]["system_profile"]["yum_repos"] if x["enabled"]
#         ],
#         # we might also need repository_paths for RHUI systems but it might not be available in the system_profile
#         "basearch": system_profile["results"][0]["system_profile"]["arch"],
#         "extended": True,
#     }
#     vmaas_modules = []
#     for module in system_profile["results"][0]["system_profile"]["dnf_modules"]:
#         vmaas_modules.append({"module_name": module["name"], "module_stream": module["stream"]})
#     if vmaas_modules:
#         vmaas_json["modules_list"] = vmaas_modules
#     if releasever := system_profile["results"][0].get("rhsm", {}).get("version"):
#         vmaas_json["releasever"] = releasever
#     return vmaas_json
