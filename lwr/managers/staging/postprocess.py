from galaxy.util import copy_to_path
from lwr.lwr_client import action_mapper
from lwr.lwr_client import staging
from lwr.lwr_client.staging import LwrOutputs
from lwr.lwr_client.staging.down import ResultsCollector

import logging
log = logging.getLogger(__name__)


def postprocess(job_directory):
    # Returns True iff outputs were collected.
    try:
        staging_config = job_directory.load_metadata("staging_config", None)
        if staging_config:
            return __collect_outputs(job_directory, staging_config)
    finally:
        job_directory.write_file("postprocessed", "")
    return False


def __collect_outputs(job_directory, staging_config):
    collected = True
    if "action_mapper" in staging_config:
        file_action_mapper = action_mapper.FileActionMapper(config=staging_config["action_mapper"])
        client_outputs = staging.ClientOutputs.from_dict(staging_config["client_outputs"])
        lwr_outputs = __lwr_outputs(job_directory)
        output_collector = LwrServerOutputCollector(job_directory)
        results_collector = ResultsCollector(output_collector, file_action_mapper, client_outputs, lwr_outputs)
        collection_failure_exceptions = results_collector.collect()
        if collection_failure_exceptions:
            log.warn("Failures collecting results %s" % collection_failure_exceptions)
            collected = False
    return collected


class LwrServerOutputCollector(object):

    def __init__(self, job_directory):
        self.job_directory = job_directory

    def collect_output(self, results_collector, output_type, action, name):
        # Not using input path, this is because action knows it path
        # in this context.
        if action.staging_action_local:
            return  # Galaxy (client) will collect output.

        lwr_path = self.job_directory.calculate_path(name, output_type)
        # TODO: Handle other action types...
        if action.action_type == "remote_copy":
            with open(lwr_path, "rb") as f:
                copy_to_path(f, action.path)
        else:
            log.warn("Unable to handle action %s on LWR side." % action)


def __lwr_outputs(job_directory):
    working_directory_contents = job_directory.working_directory_contents()
    output_directory_contents = job_directory.outputs_directory_contents()
    return LwrOutputs(
        working_directory_contents,
        output_directory_contents,
    )

__all__ = [postprocess]
