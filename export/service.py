import csv
import boto3
from datetime import datetime
import logging
import os
import shutil
import traceback
import uuid
from logging.config import dictConfig
from amaasutils.logging_utils import DEFAULT_LOGGING
from amaascore.transactions.interface import TransactionsInterface

dictConfig(DEFAULT_LOGGING)
logger = logging.getLogger()
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

def handler(event, context):
    output_bucket = os.environ['OUTPUT_BUCKET']
    asset_manager_id = event['asset_manager_id']
    transactions_api = TransactionsInterface(environment=ENVIRONMENT)
    positions = transactions_api.positions_by_asset_manager(
        asset_manager_id=asset_manager_id)
    positions = sorted(positions, key=lambda p: (p.book_id, p.asset_id))
    rows = []
    for position in positions:
        position_dict = {key: str(value)
                         for key, value in position.to_dict().items()
                         if key not in position.amaas_model_attributes()}
        if not rows:
            rows.append(position_dict.keys())
        rows.append(position_dict.values())
    # Write positions to csv
    scratch_dir = f'/tmp/{uuid.uuid4().hex}'
    try:
        os.mkdir(scratch_dir)
        filename = f'positions_{datetime.utcnow().timestamp()}.csv'
        filepath = os.path.join(scratch_dir, filename)
        with open(filepath, 'w') as output_file:
            writer = csv.writer(output_file, delimiter=',')
            for row in rows:
                writer.writerow(row)
        # upload output to S3
        s3_client = boto3.client('s3')
        s3_client.upload_file(filepath, output_bucket, filename)
    except:
        logger.error('Failed to write output file. %s', traceback.format_exc())
        raise
    finally:
        logger.info('Cleaning up working directory %s', scratch_dir)
        shutil.rmtree(scratch_dir)
    return event
