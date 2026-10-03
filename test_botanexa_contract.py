import unittest
import json
import sys

# Global Mock Setup for GenLayer `gl` namespace
class MockMessage:
    def __init__(self):
        self.sender_address = "0xaaaa"
        self.value = 1000000000000000000

class MockResult:
    def __init__(self, calldata):
        self.calldata = calldata

class MockNondetWeb:
    @staticmethod
    def render(url, mode='text'):
        if "fraud" in url:
            return "corruption fraud investigation"
        return "1000000000 trees planted in Khyber Pakhtunkhwa, Pakistan. Native regional trees."

class MockNondetLLM:
    @staticmethod
    def call(prompt, schema):
        if "fraud" in prompt:
            return '{"is_accurate": false, "source_provenance_valid": true, "location_match": true, "species_safe": true, "tree_count_reasonable": true, "reasoning": "Rejected due to fraud", "carbon_sequestration_tons": "0", "ecological_suitability": "None", "ecological_role": "", "image_url": ""}'
        return '{"is_accurate": true, "source_provenance_valid": true, "location_match": true, "species_safe": true, "tree_count_reasonable": true, "reasoning": "Valid", "carbon_sequestration_tons": "500", "ecological_suitability": "Good", "ecological_role": "Soil", "image_url": "http://img"}'

class MockVM:
    class Return:
        pass
    class Result:
        def __init__(self, calldata):
            self.calldata = calldata
    class UserError(Exception):
        pass
    @staticmethod
    def run_nondet_unsafe(leader_fn, validator_fn):
        res = leader_fn()
        return res

class MockEqPrinciple:
    def __init__(self, val):
        pass

class MockAddress:
    def __init__(self, address):
        self.address = address
    def __str__(self):
        return self.address

class MockRecipient:
    transfers = []
    def __init__(self, address):
        self.address = str(address)
    def emit_transfer(self, value, **kwargs):
        MockRecipient.transfers.append({"to": self.address, "value": value})

class MockContract:
    def __init__(self):
        self.balance = 100 * 1000000000000000000 # 100 GEN

class MockDecorator:
    def __call__(self, fn):
        return fn
    @property
    def payable(self):
        return self
    @property
    def write(self):
        return self
    @property
    def view(self):
        return self

class MockGL:
    def __init__(self):
        self.message = MockMessage()
        
        # Define nondet object that has exec_prompt
        class NondetObj:
            web = MockNondetWeb
            def exec_prompt(self, prompt_str):
                return MockNondetLLM.call(prompt_str, None)
        
        self.nondet = NondetObj()
        self.vm = MockVM
        self.eq_principle = MockEqPrinciple
        self.Contract = MockContract
        self.public = type('obj', (object,), {'write': MockDecorator(), 'view': MockDecorator()})()
        self.evm = type('obj', (object,), {'contract_interface': MockDecorator()})()

# Inject the mock `gl` into sys.modules so `botanexa_contract.py` can import it
mock_genlayer = type('genlayer', (object,), {'gl': MockGL(), 'u256': int, 'TreeMap': dict, 'Address': MockAddress})
sys.modules['genlayer'] = mock_genlayer

from botanexa_contract import BotanexaRegistry

class BotanexaRegistryTest(unittest.TestCase):
    def setUp(self):
        MockRecipient.transfers = []
        self.contract = BotanexaRegistry()
        # Need to manually inject the balance property for the mock
        self.contract.balance = 100 * 1000000000000000000
        
        # Inject Recipient mock specifically for tests
        import botanexa_contract
        botanexa_contract._Recipient = MockRecipient
        botanexa_contract.gl = mock_genlayer.gl

    def test_full_reward_claim_lifecycle(self):
        mock_genlayer.gl.message.sender_address = MockAddress("0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        
        # Propose
        self.contract.propose_offset("Amazonia Canopy", "-3.465, -62.215", "Mahogany", 5000, "https://example.org")
        
        pending = int(self.contract.pending_rewards.get("0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "0"))
        self.assertEqual(pending, 2 * 1000000000000000000)

        # Withdraw
        self.contract.withdraw_rewards()
        
        self.assertEqual(len(MockRecipient.transfers), 1)
        self.assertEqual(MockRecipient.transfers[0]["to"], "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        self.assertEqual(MockRecipient.transfers[0]["value"], 2 * 1000000000000000000)

        self.assertEqual(int(self.contract.pending_rewards["0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]), 0)

        with self.assertRaises(Exception) as ctx:
            self.contract.withdraw_rewards()
        self.assertIn("No rewards available", str(ctx.exception))

    def test_real_burning_on_fraudulent_claim(self):
        mock_genlayer.gl.message.sender_address = MockAddress("0xcccccccccccccccccccccccccccccccccccccccc")
        
        # Trigger rejection
        self.contract.propose_offset("Fake Desert Trees", "0.0, 0.0", "Kudzu", 999999, "https://fraud.org")
        
        self.assertEqual(int(self.contract.pending_rewards.get("0xcccccccccccccccccccccccccccccccccccccccc", "0")), 0)

        self.assertEqual(len(MockRecipient.transfers), 1)
        self.assertEqual(MockRecipient.transfers[0]["to"], "0x0000000000000000000000000000000000000000")
        self.assertEqual(MockRecipient.transfers[0]["value"], 1000000000000000000)

    def test_duplicate_project_rejection(self):
        mock_genlayer.gl.message.sender_address = MockAddress("0xdddddddddddddddddddddddddddddddddddddddd")
        self.contract.propose_offset("UniqueProject", "Coords", "Oak", 100, "https://valid.com")
        with self.assertRaises(Exception) as ctx:
            self.contract.propose_offset("uniqueproject", "Coords", "Oak", 100, "https://valid.com")
        self.assertIn("already verified", str(ctx.exception))

    def test_invalid_url_validation(self):
        mock_genlayer.gl.message.sender_address = MockAddress("0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
        with self.assertRaises(Exception) as ctx:
            self.contract.propose_offset("Project", "Coords", "Pine", 10, "ftp://badurl.com")
        self.assertIn("Invalid evidence_url", str(ctx.exception))

    def test_treasury_insufficient(self):
        mock_genlayer.gl.message.sender_address = MockAddress("0xffffffffffffffffffffffffffffffffffffffff")
        # Artificially inflate pending rewards so balance can't cover it
        self.contract.total_pending_rewards = 100 * 1000000000000000000
        with self.assertRaises(Exception) as ctx:
            self.contract.propose_offset("TreasuryTest", "Coords", "Oak", 100, "https://test.org")
        self.assertIn("enough treasury funds", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
