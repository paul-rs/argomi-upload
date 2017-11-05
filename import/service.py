import os
import boto3
import csv
import logging
import shutil
import traceback
import uuid
import zipfile
from dateutil.parser import parse
from logging.config import dictConfig
from amaasutils.logging_utils import DEFAULT_LOGGING
from amaasutils.case import to_snake_case
from amaascore.assets.foreign_exchange import ForeignExchangeSpot, ForeignExchangeForward
from amaascore.assets.interface import AssetsInterface
from amaascore.books.interface import BooksInterface
from amaascore.books.book import Book
from amaascore.parties.interface import PartiesInterface
from amaascore.parties.individual import Individual
from amaascore.parties.fund import Fund
from amaascore.parties.broker import Broker
from amaascore.transactions.interface import TransactionsInterface
from amaascore.transactions.transaction import Transaction
from amaascore.transactions.children import Charge, Rate, Party as TransactionParty
from amaascore.core.reference import Reference


dictConfig(DEFAULT_LOGGING)
logger = logging.getLogger()

S3_CLIENT = boto3.client('s3')
PARTY_TYPES = [Individual, Fund, Broker]
BOOK_FIELD_MAPPINGS = {'owning_party': 'party_id', 'trading_owner': 'owner_id'}
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
ABORT_THRESHOLD = 15 * 1000 # seconds * milliseconds
PARTIES_PREFIX = 'Parties.'
CHARGES_PREFIX = 'Charges.'
RATES_PREFIX = 'Rates.'


def handler(event, context):
    asset_manager_id = event['asset_manager_id']
    s3_bucket = event['s3_bucket']
    s3_key = event['s3_key']
    import_type = event['import_type']
    resume_index = event.get('resume_index', 0)
    aborted = event.get('aborted', False)
    processed_files = event.get('processed_files', [])

    scratch_dir = f'/tmp/{uuid.uuid4().hex}'
    try:
        # download the data file from S3
        os.mkdir(scratch_dir)
        download_path = f'{scratch_dir}/{s3_key}'
        logger.info('Downloading file %s from %s to %s', s3_key, s3_bucket, download_path)
        S3_CLIENT.download_file(s3_bucket, s3_key, download_path)
        import_files = _extract_file(download_path, import_type)

        for file in import_files:
            filename = os.path.basename(file)
            if filename in processed_files:
                continue
            logger.info('Importing data from %s', filename)
            aborted, count = _import(asset_manager_id, file, import_type, context, resume_index)

            if aborted:
                resume_index = count
                break
            processed_files.append(filename)
            resume_index = 0

        event['aborted'] = aborted
        event['resume_index'] = resume_index
        event['processed_files'] = processed_files
    except:
        logger.error(traceback.format_exc())
        raise
    finally:
        logger.info('Cleaning up working directory %s', scratch_dir)
        shutil.rmtree(scratch_dir)
    return event


def _import_book(asset_manager_id, rowdata):
    rowdata = {to_snake_case(key): value for key, value in rowdata.items()}
    if not rowdata.get('book_id'):
        return
    mapped_fields = [{mapped_field: rowdata.pop(field)} for field, mapped_field in BOOK_FIELD_MAPPINGS.items()]
    [rowdata.update(field) for field in mapped_fields]
    book = Book(**rowdata)
    book_api = BooksInterface(environment=ENVIRONMENT)
    existing_book = book_api.search(asset_manager_id=asset_manager_id, book_ids=[book.book_id])
    book_api.new(book) if not existing_book else book_api.amend(book)
    return book


def _import_party(asset_manager_id, rowdata):
    rowdata = {to_snake_case(key): value for key, value in rowdata.items()}
    if not rowdata.get('party_id'):
        return
    party_type = next((p for p in PARTY_TYPES if p.__name__ == rowdata.get('party_type')), None)
    if not party_type:
        return
    party = party_type(**rowdata)
    parties_api = PartiesInterface(environment=ENVIRONMENT)
    existing_party = parties_api.search(asset_manager_id=asset_manager_id, party_ids=[party.party_id])
    parties_api.new(party) if not existing_party else parties_api.amend(party)
    return party


def _import_transaction(asset_manager_id, rowdata):
    charge_columns = [c for c in rowdata.keys() if c.startswith(CHARGES_PREFIX)]
    charges = {column.replace(CHARGES_PREFIX, ''): rowdata.pop(column)
               for column in charge_columns if rowdata.get(column)}
    party_columns = [c for c in rowdata.keys() if c.startswith(PARTIES_PREFIX)]
    parties = {column.replace(PARTIES_PREFIX, ''): rowdata.pop(column)
               for column in party_columns if rowdata.get(column)}
    rate_columns = [c for c in rowdata.keys() if c.startswith(RATES_PREFIX)]
    rates = {column.replace(RATES_PREFIX, ''): rowdata.pop(column)
             for column in rate_columns if rowdata.get(column)}
    rowdata = {to_snake_case(key): value for key, value in rowdata.items()}

    asset_type = rowdata.pop('asset_type')
    if not asset_type:
        return
    asset_id = rowdata['asset_id']
    settlement_date = parse(rowdata['settlement_date'])
    if asset_type in ['ForeignExchangeSpot', 'ForeignExchangeForward']:
        underlying = asset_id
        # this should be handled by our SDK ideally
        prefix, model = ('SPT', ForeignExchangeSpot) if asset_type == 'ForeignExchangeSpot' \
                                                     else ('FWD', ForeignExchangeForward)
        asset_id = f'{prefix}{asset_id}{settlement_date.strftime("%Y%m%d")}'
        rowdata['asset_id'] = asset_id
        params = {'asset_manager_id': asset_manager_id,
                  'asset_id': asset_id,
                  'underlying': underlying,
                  'settlement_date': rowdata['settlement_date'],
                  'currency': rowdata['transaction_currency']}
        if asset_type == 'ForeignExchangeForward':
            params['fixing_date'] = rowdata.get('fixing_date')
            params['forward_rate'] = rowdata['price']
        asset = model(**params)
        asset.references['CCY Pair'] = Reference(underlying, reference_primary=True)
        asset_api = AssetsInterface(environment=ENVIRONMENT)
        existing_asset = asset_api.search(asset_manager_id=asset_manager_id, asset_ids=[asset_id])
        asset = asset_api.new(asset) if not existing_asset else asset_api.amend(asset)

    transaction = Transaction(**rowdata)
    transaction_api = TransactionsInterface(environment=ENVIRONMENT)
    existing_transaction = transaction_api.search(asset_manager_id=asset_manager_id,
                                                  transaction_ids=[rowdata['transaction_id']])
    for party_type, party_id in parties.items():
        transaction.parties[party_type] = TransactionParty(party_id)
    for charge_type, charge_value in charges.items():
        transaction.charges[charge_type] = Charge(charge_value, rowdata['transaction_currency'])
    for rate_type, rate_value in rates.items():
        transaction.rates[rate_type] = Rate(rate_value)
    transaction_api.new(transaction) if not existing_transaction else transaction_api.amend(transaction)
    return transaction


def _import(asset_manager_id, filename, import_type, context, resume_index):
    import_funcs = {'parties': _import_party,
                    'books': _import_book,
                    'transactions': _import_transaction}
    count = 0
    with open(filename, 'r') as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader)
        for row in reader:
            count +=1
            # skip already processed row from previous execution
            if count <= resume_index:
                continue
            try:
                rowdata = {key: value for (key, value) in zip(header, row)}
                rowdata['asset_manager_id'] = asset_manager_id
                result = import_funcs[import_type](asset_manager_id, rowdata)
                if result:
                    logger.info('Updated record %s', result)
            except Exception:
                logger.error('Failed to import row %s: %s', rowdata, traceback.format_exc())
                raise

            # abort current execution before hitting timeout
            if context is not None: # executing out of lambda (testing)
                remaining_time = context.get_remaining_time_in_millis()
                if remaining_time <= ABORT_THRESHOLD:
                    return True, count
    return False, count


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
    elif download_path.endswith('.csv'):
        return [download_path] if name.startswith(import_type) else []
    else:
        raise ValueError('Unrecognized file type %s' % os.path.splitext(download_path)[1])

