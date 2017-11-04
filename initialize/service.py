import logging
from logging.config import dictConfig
from amaasutils.logging_utils import DEFAULT_LOGGING

dictConfig(DEFAULT_LOGGING)
logger = logging.getLogger()


def handler(event, context):
    event['import_type'] = None
    return event
    
    # TODO: get the company AMID here. Add SDK method to retrieve relationship from user AMID
    # am_api = AssetManagersInterface(environment='production')
    # return None

    

