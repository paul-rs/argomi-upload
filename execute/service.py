import os
import boto3
import logging
import json
from logging.config import dictConfig
from amaasutils.logging_utils import DEFAULT_LOGGING


dictConfig(DEFAULT_LOGGING)
logger = logging.getLogger()


def handler(event, context):
    s3 = event['Records'][0]['s3']
    s3_bucket = s3['bucket']['name']
    s3_key = s3['object']['key']

    payload = {'s3_bucket': s3_bucket,
               's3_key': s3_key}
    asset_manager_id = os.environ.get('AMID')
    if asset_manager_id:
        payload['asset_manager_id'] = int(asset_manager_id)

    states_arn = os.environ['STATEMACHINEARN']
    client = boto3.client('stepfunctions')
    return client.start_execution(stateMachineArn=states_arn, input=json.dumps(payload))

