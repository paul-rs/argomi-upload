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
    # return event
    
    am_api = AssetManagersInterface(environment=ENVIRONMENT)
    user_attributes = jwt.decode(am_api.session.tokens['IdToken'], verify=False)
    user_amid = user_attributes.get('custom:asset_manager_id')
    if not user_amid:
        raise AttributeError('Invalid credentials. Could not determine user asset manager id.')
    
    relationships = am_api.retrieve_user_relationships(user_asset_manager_id=user_amid)
    if not relationships:
        raise ValueError('User does not have any Active relationships')
    asset_manager_id = None
    # Find the first non-demo account
    for relationship in relationships:
        asset_manager = am_api.retrieve(relationship.asset_manager_id)
        if asset_manager.account_type != 'Demo':
            asset_manager_id = asset_manager.asset_manager_id
            break;
    
    if not asset_manager_id:
        raise ValueError('Could not find a valid asset manager for the specified user.')
    
    event['asset_manager_id'] = asset_manager_id
    return event

def _extract_file(download_path, import_type):
    scratch_dir = os.path.dirname(download_path)
    extract_dir = f'{scratch_dir}/{uuid.uuid4().hex}'
    name, extension = os.path.splitext(os.path.basename(download_path))

    if extension == '.zip':
        os.makedirs(extract_dir)
        zip_ref = zipfile.ZipFile(download_path, 'r')
        logger.info('Extracting %s into %s', download_path, extract_dir)
        zip_ref.extractall(extract_dir)
        zip_ref.close()
        import_files = [f'{extract_dir}/{filename}'
                        for filename in os.listdir(extract_dir)
                        if filename.startswith(import_type)]
        return import_files
    else if download_path.endswith('.csv'):
        return [download_path]
    else:
        raise ValueError('Unrecognized file type %s' % os.path.splitext(download_path)[1])

