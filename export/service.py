import os
from amaascore.transactions.interface import TransactionsInterface

ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

def handler(event, context):
    asset_manager_id = event['asset_manager_id']
    transactions_api = TransactionsInterface(environment=ENVIRONMENT)
    positions = transactions_api.positions_by_asset_manager(asset_manager_id=asset_manager_id)
    positions = sorted(positions, key=lambda p: (p.book_id, p.asset_id))
    rows = []
    header = []
    for position in positions:
        position_dict = {key: str(value) for key, value in position.to_dict().items()
                         if key not in position.amaas_model_attributes() + ['asset_manager_id']}
        rows.append(position_dict.values())
        if not header:
            header = position_dict.keys()
    # TODO: write to CSV then upload to S3
          
    return event
