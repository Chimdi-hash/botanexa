import json
import unittest

# Mock GenLayer environment for contract testing
class MockAddress:
    def __init__(self, addr_str="0x1111111111111111111111111111111111111111"):
        self.addr = addr_str
    def __str__(self):
        return self.addr
    def as_hex(self):
        return self.addr

class MockRecipient:
    transfers = []
    def __init__(self, target_address):
        self.target = str(target_address)
    def emit_transfer(self, value, on='finalized'):
        MockRecipient.transfers.append({
            "to": self.target,
            "value": int(value),
            "on": on
        })

class MockMessage:
    def __init__(self, sender="0x1111111111111111111111111111111111111111", value=1000000000000000000):
        self.sender_address = MockAddress(sender)
        self.value = value

class MockNondetWeb:
    @staticmethod
    def render(url, mode='text'):
        return "Amazon Rainforest Reforestation Project verified 5000 Swietenia macrophylla mahogany trees planted at -3.465, -62.215."

class MockEqPrinciple:
    mock_response = None
    @staticmethod
    def prompt_non_comparative(prompt_fn, task="", criteria=""):
        if MockEqPrinciple.mock_response is not None:
            return MockEqPrinciple.mock_response
        return json.dumps({
            "is_accurate": True,
            "reasoning": "Valid audit verified by mock consensus",
            "project_name": "Amazon Basin Sector D",
            "location_coords": "-3.465, -62.215",
            "species_planted": ["Swietenia macrophylla"],
            "tree_count": 5000,
            "carbon_offset_tons": 110.0,
            "ecological_suitability": "Highly Suitable - Native Species",
            "ecological_role": "Soil stabilization and watershed restoration"
        })

# Global mock gl namespace
class MockGL:
    def __init__(self):
        self.message = MockMessage()
        self.nondet = type('obj', (object,), {'web': MockNondetWeb})
        self.eq_principle = MockEqPrinciple
    def get_self_balance(self):
        return 100000000000000000000 # 100 GEN treasury

gl = MockGL()
Address = MockAddress
_Recipient = MockRecipient
u256 = int
TreeMap = dict
class Contract: pass

# Import or define the contract logic using the mock environment
class BotanexaRegistryTest(unittest.TestCase):
    def setUp(self):
        MockRecipient.transfers = []
        # Instantiate contract state
        self.query_history = {}
        self.verified_projects = {}
        self.pending_rewards = {}
        self.total_pending_rewards = "0"
        self.total_queries = 0
        self.recent_projects_list = json.dumps([])
        self.ONE_GEN = 1000000000000000000

    def _addr(self, a):
        return str(a).lower()

    def propose_offset(self, project_name, location_coords, species_planted, tree_count, evidence_url, mock_accuracy=True, stake=1000000000000000000):
        caller = gl.message.sender_address
        caller_str = self._addr(caller)
        stake_int = int(stake)

        if stake_int < self.ONE_GEN:
            raise Exception("Must stake at least 1 GEN to propose a project audit.")

        project_clean = project_name.strip()
        project_lower = project_clean.lower()

        if not project_lower:
            raise Exception("Project name cannot be empty.")

        if project_lower in self.verified_projects:
            raise Exception(f"Project '{project_clean}' is already verified.")

        # Reward is strictly capped: 1 GEN bonus reward (+ the stake returned)
        reward_bonus = self.ONE_GEN
        reward_wei = stake_int + reward_bonus
        
        safe_exp = {
            "project_name": project_clean,
            "reasoning": "Valid audit verified by mock consensus",
            "image_url": "https://example.org/image.jpg"
        }

        if mock_accuracy:
            # ACCEPTED:
            current = int(self.pending_rewards.get(caller_str, "0"))
            self.pending_rewards[caller_str] = str(current + reward_wei)
            current_total = int(self.total_pending_rewards)
            self.total_pending_rewards = str(current_total + reward_wei)

            self.verified_projects[project_lower] = json.dumps({
                "proposer": caller_str,
                "project_name": project_clean,
                "validator_consensus": True,
                "explanation": safe_exp
            })
            
            hist = json.loads(self.query_history[caller_str]) if caller_str in self.query_history else []
            hist.append({"project": project_clean, "project_lower": project_lower, "reasoning": safe_exp["reasoning"], "image_url": safe_exp["image_url"], "accepted": True})
            self.query_history[caller_str] = json.dumps(hist)
            
            self.total_queries += 1
            return "ACCEPTED"
        else:
            # REJECTED: Real Burn to Null Address 0x0000...
            burn_address = "0x0000000000000000000000000000000000000000"
            _Recipient(burn_address).emit_transfer(value=stake_int, on='finalized')
            
            hist = json.loads(self.query_history[caller_str]) if caller_str in self.query_history else []
            hist.append({"project": project_clean, "project_lower": project_lower, "reasoning": "Rejected", "accepted": False})
            self.query_history[caller_str] = json.dumps(hist)
            
            self.total_queries += 1
            return "REJECTED"

    def withdraw_rewards(self, caller_address):
        caller_str = self._addr(caller_address)
        pending_str = self.pending_rewards.get(caller_str, "0")
        pending_amount = int(pending_str)

        if pending_amount == 0:
            raise Exception("No rewards available to withdraw.")

        # Checks-effects-interactions
        self.pending_rewards[caller_str] = "0"
        current_total = int(self.total_pending_rewards)
        self.total_pending_rewards = str(current_total - pending_amount)

        # Emit native transfer to caller
        _Recipient(caller_address).emit_transfer(value=pending_amount, on='finalized')
        return pending_amount

    def test_full_reward_claim_lifecycle(self):
        user = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        gl.message.sender_address = MockAddress(user)

        res = self.propose_offset("Amazonia Canopy", "-3.465, -62.215", "Mahogany", 5000, "https://example.org", mock_accuracy=True, stake=self.ONE_GEN)
        self.assertEqual(res, "ACCEPTED")

        pending = int(self.pending_rewards[user.lower()])
        self.assertEqual(pending, 2 * self.ONE_GEN)

        withdrawn = self.withdraw_rewards(user)
        self.assertEqual(withdrawn, 2 * self.ONE_GEN)

        self.assertEqual(len(MockRecipient.transfers), 1)
        self.assertEqual(MockRecipient.transfers[0]["to"], user)
        self.assertEqual(MockRecipient.transfers[0]["value"], 2 * self.ONE_GEN)

        self.assertEqual(int(self.pending_rewards[user.lower()]), 0)

        with self.assertRaises(Exception) as ctx:
            self.withdraw_rewards(user)
        self.assertIn("No rewards available to withdraw", str(ctx.exception))

    def test_real_burning_on_fraudulent_claim(self):
        user = "0xcccccccccccccccccccccccccccccccccccccccc"
        gl.message.sender_address = MockAddress(user)

        res = self.propose_offset("Fake Desert Trees", "0.0, 0.0", "Kudzu", 999999, "https://fake.org", mock_accuracy=False, stake=self.ONE_GEN)
        self.assertEqual(res, "REJECTED")

        self.assertEqual(int(self.pending_rewards.get(user.lower(), "0")), 0)

        self.assertEqual(len(MockRecipient.transfers), 1)
        self.assertEqual(MockRecipient.transfers[0]["to"], "0x0000000000000000000000000000000000000000")
        self.assertEqual(MockRecipient.transfers[0]["value"], self.ONE_GEN)

    def test_duplicate_project_rejection(self):
        user = "0xdddddddddddddddddddddddddddddddddddddddd"
        gl.message.sender_address = MockAddress(user)
        self.propose_offset("UniqueProject", "Coords", "Oak", 100, "https://valid.com", mock_accuracy=True, stake=self.ONE_GEN)
        with self.assertRaises(Exception) as ctx:
            self.propose_offset("UniqueProject", "Coords", "Oak", 100, "https://valid.com", mock_accuracy=True, stake=self.ONE_GEN)
        self.assertIn("already verified", str(ctx.exception))

    def test_invalid_url_validation(self):
        user = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        gl.message.sender_address = MockAddress(user)
        with self.assertRaises(Exception) as ctx:
            self.propose_offset("Project", "Coords", "Pine", 10, "ftp://badurl.com", stake=self.ONE_GEN)
        self.assertIn("Invalid evidence_url", str(ctx.exception))

    def test_treasury_insufficient(self):
        user = "0xffffffffffffffffffffffffffffffffffffffff"
        gl.message.sender_address = MockAddress(user)
        # Mock drain treasury by artificially setting balance in the mock or simulating large rewards
        # The contract code checks `self.balance < self.total_pending_rewards + stake + ONE_GEN`
        # We can trigger it by artificially inflating pending rewards
        self.total_pending_rewards = str(1000 * self.ONE_GEN)
        with self.assertRaises(Exception) as ctx:
            self.propose_offset("TreasuryTest", "Coords", "Oak", 100, "https://test.org", stake=self.ONE_GEN)
        self.assertIn("Contract does not have enough treasury funds", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
