import logging
import jwt
import os
from logging.config import dictConfig
from amaasutils.logging_utils import DEFAULT_LOGGING
from amaascore.asset_managers.interface import AssetManagersInterface

dictConfig(DEFAULT_LOGGING)
logger = logging.getLogger()
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

def handler(event, context):
    event['import_type'] = None

    am_api = AssetManagersInterface(environment=ENVIRONMENT)
    token = am_api.session.tokens['IdToken']
    user_attributes = jwt.decode(token, verify=False)
    user_amid = user_attributes.get('custom:asset_manager_id')
    if not user_amid:
        raise AttributeError(
            'Invalid credentials. Could not determine user asset manager id.')

    relationships = am_api.retrieve_user_relationships(
        user_asset_manager_id=user_amid)
    if not relationships:
        raise ValueError('User does not have any Active relationships')

    asset_manager_id = None
    # Find the first non-demo account
    for relationship in relationships:
        asset_manager = am_api.retrieve(relationship.asset_manager_id)
        if asset_manager.account_type != 'Demo':
            asset_manager_id = asset_manager.asset_manager_id
            break

    if not asset_manager_id:
        raise ValueError(
            'Could not find a valid asset manager for the specified user.')

    event['asset_manager_id'] = asset_manager_id
    return event
