# -*- coding: utf-8 -*-
from parsedmarc.log import logger
from azure.core.exceptions import HttpResponseError
from azure.identity import ClientSecretCredential
from azure.monitor.ingestion import LogsIngestionClient


class LogAnalyticsException(Exception):
    """Raised when an Elasticsearch error occurs"""


class LogAnalyticsConfig():
    """
    The LogAnalyticsConfig class is used to define the configuration
    for the Log Analytics Client.

    Properties:
        client_id (str):
            The client ID of the service principle.
        client_secret (str):
            The client secret of the service principle.
        tenant_id (str):
            The tenant ID where
            the service principle resides.
        dce (str):
            The Data Collection Endpoint (DCE)
            used by the Data Collection Rule (DCR).
        dcr_immutable_id (str):
            The immutable ID of
            the Data Collection Rule (DCR).
        dcr_aggregate_stream (str):
            The Stream name where
            the Aggregate DMARC reports
            need to be pushed.
        dcr_forensic_stream (str):
            The Stream name where
            the Forensic DMARC reports
            need to be pushed.
    """
    def __init__(
            self,
            client_id: str,
            client_secret: str,
            tenant_id: str,
            dce: str,
            dcr_immutable_id: str,
            dcr_aggregate_stream: str,
            dcr_forensic_stream: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.dce = dce
        self.dcr_immutable_id = dcr_immutable_id
        self.dcr_aggregate_stream = dcr_aggregate_stream
        self.dcr_forensic_stream = dcr_forensic_stream


class LogAnalyticsClient(object):
    """
    The LogAnalyticsClient is used to push
    the generated DMARC reports to Log Analytics
    via Data Collection Rules.
    """
    def __init__(
            self,
            client_id: str,
            client_secret: str,
            tenant_id: str,
            dce: str,
            dcr_immutable_id: str,
            dcr_aggregate_stream: str,
            dcr_forensic_stream: str):
        self.conf = LogAnalyticsConfig(
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            dce=dce,
            dcr_immutable_id=dcr_immutable_id,
            dcr_aggregate_stream=dcr_aggregate_stream,
            dcr_forensic_stream=dcr_forensic_stream
        )
        if (
                not self.conf.client_id or
                not self.conf.client_secret or
                not self.conf.tenant_id or
                not self.conf.dce or
                not self.conf.dcr_immutable_id or
                not self.conf.dcr_aggregate_stream or
                not self.conf.dcr_forensic_stream):
            raise LogAnalyticsException(
                "Invalid configuration. " +
                "One or more required settings are missing.")

    def publish_json(
            self,
            results,
            logs_client: LogsIngestionClient,
            dcr_stream: str):
        """
        Background function to publish given
        DMARC reprot to specific Data Collection Rule.

        Args:
            results (list):
                The results generated by parsedmarc.
            logs_client (LogsIngestionClient):
                The client used to send the DMARC reports.
            dcr_stream (str):
                The stream name where the DMARC reports needs to be pushed.
        """
        try:
            logs_client.upload(self.conf.dcr_immutable_id, dcr_stream, results)
        except HttpResponseError as e:
            raise LogAnalyticsException(
                "Upload failed: {error}"
                .format(error=e))

    def publish_results(
            self,
            results,
            save_aggregate: bool,
            save_forensic: bool):
        """
        Function to publish DMARC reports to Log Analytics
        via Data Collection Rules (DCR).
        Look below for docs:
        https://learn.microsoft.com/en-us/azure/azure-monitor/logs/logs-ingestion-api-overview

        Args:
            results (list):
                The DMARC reports (Aggregate & Forensic)
            save_aggregate (bool):
                Whether Aggregate reports can be saved into Log Analytics
            save_forensic (bool):
                Whether Forensic reports can be saved into Log Analytics
        """
        conf = self.conf
        credential = ClientSecretCredential(
            tenant_id=conf.tenant_id,
            client_id=conf.client_id,
            client_secret=conf.client_secret
        )
        logs_client = LogsIngestionClient(conf.dce, credential=credential)
        if(
                results['aggregate_reports'] and
                conf.dcr_aggregate_stream and
                len(results['aggregate_reports']) > 0 and
                save_aggregate):
            logger.info("Publishing aggregate reports.")
            self.publish_json(
                results['aggregate_reports'],
                logs_client,
                conf.dcr_aggregate_stream)
            logger.info("Successfully pushed aggregate reports.")
        if(
                results['forensic_reports'] and
                conf.dcr_forensic_stream and
                len(results['forensic_reports']) > 0 and
                save_forensic):
            logger.info("Publishing forensic reports.")
            self.publish_json(
                results['forensic_reports'],
                logs_client,
                conf.dcr_forensic_stream)
            logger.info("Successfully pushed forensic reports.")
