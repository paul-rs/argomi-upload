import random
import unittest
from mock import patch
from amaasutils.random_utils import random_string
from service import handler, _import_party, _import_book, _import_transaction


class ImportTests(unittest.TestCase):

    def setUp(self):
        self.asset_manager_id = random.randint(1, 2**31-1)
    
    @patch('service.boto3')
    @patch('service.PartiesInterface')
    def test_ImportIndividualParty(self, mock_interface, mock_boto3):
        data = {'PartyId': random_string(8),
                'PartyType': 'Individual',
                'DisplayName': random_string(12),
                'Surname': random_string(10),
                'GivenNames': random_string(10),
                'AssetManagerId': self.asset_manager_id}
        mock_interface.return_value.search.return_value = []
        result = _import_party(self.asset_manager_id, data)
        self.assertEqual(type(result).__name__, data['PartyType'])
        self.assertEqual(data['Surname'], result.surname)
        self.assertEqual(data['GivenNames'], result.given_names)
        mock_interface.return_value.search.assert_called_once()
        mock_interface.return_value.new.assert_called_once()

        mock_interface.reset_mock()
        mock_interface.return_value.search.return_value = [result]
        result = _import_party(self.asset_manager_id, data)
        mock_interface.return_value.search.assert_called_once()
        mock_interface.return_value.amend.assert_called_once()
    

    @patch('service.boto3')
    @patch('service.PartiesInterface')
    def test_ImportCompany(self, mock_interface, mock_boto3):
        for party_type in ['Fund', 'Broker']:
            data = {'PartyId': random_string(8),
                    'PartyType': party_type,
                    'DisplayName': random_string(12),
                    'LegalName': random_string(10),
                    'Description': random_string(20),
                    'BaseCurrency': random_string(3),
                    'AssetManagerId': self.asset_manager_id}
            mock_interface.reset_mock()
            mock_interface.return_value.search.return_value = []
            result = _import_party(self.asset_manager_id, data)
            self.assertEqual(type(result).__name__, data['PartyType'])
            self.assertEqual(data['DisplayName'], result.display_name)
            self.assertEqual(data['LegalName'], result.legal_name)
            self.assertEqual(data['Description'], result.description)
            self.assertEqual(data['BaseCurrency'], result.base_currency)
            mock_interface.return_value.search.assert_called_once()
            mock_interface.return_value.new.assert_called_once()

            mock_interface.return_value.search.return_value = [result]
            result = _import_party(self.asset_manager_id, data)
            mock_interface.return_value.amend.assert_called_once()
    
    @patch('service.boto3')
    @patch('service.BooksInterface')
    def test_ImportBook(self, mock_interface, mock_boto3):
        data = {col: random_string(random.randint(4, 8))
                for col in ['BookId', 'Description', 'BusinessUnit', 'OwningParty', 'TradingOwner', 'Reference']}
        data.update({'BookType': random.choice(['Trading', 'Counterparty', 'Wash', 'Management'])})
        data.update({'Currency': random_string(3)})
        data['AssetManagerId'] = self.asset_manager_id

        mock_interface.return_value.search.return_value = []
        result = _import_book(self.asset_manager_id, data)
        self.assertEqual(data['BookType'], result.book_type)
        mock_interface.return_value.new.assert_called_once()

        mock_interface.return_value.search.return_value = [result]
        result = _import_book(self.asset_manager_id, data)
        mock_interface.return_value.amend.assert_called_once()
    
    def test_ImportTransaction(self):
        pass
    
    def test_Handler(self):
        pass

if __name__ == '__main__':
    unittest.main()