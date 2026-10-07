import json
import pytest

# Workaround for genlayer-test Windows PermissionError on os.unlink temp file
import os
original_unlink = os.unlink
def safe_unlink(path, *args, **kwargs):
    try:
        original_unlink(path, *args, **kwargs)
    except PermissionError:
        pass
os.unlink = safe_unlink

@pytest.mark.direct
def test_full_reward_claim_lifecycle(direct_deploy, direct_vm, direct_alice, direct_bob):
    # Deploy the contract
    contract = direct_deploy("botanexa_contract.py")
    
    # Mock web fetch for Wikipedia
    evidence_url = "https://en.wikipedia.org/wiki/Billion_Tree_Tsunami"
    direct_vm.mock_web(evidence_url, {"body": "1000000000 trees planted in Khyber Pakhtunkhwa, Pakistan. Native regional trees.", "method": "GET", "status": 200})
    
    # Mock LLM prompt execution
    acceptance_json = json.dumps({
        "is_accurate": True,
        "source_provenance_valid": True,
        "location_match": True,
        "species_safe": True,
        "tree_count_reasonable": True,
        "reasoning": "Valid source and facts.",
        "carbon_sequestration_tons": "500.0",
        "ecological_suitability": "Highly suitable",
        "ecological_role": "Soil stabilization",
        "image_url": "https://example.com/tree.jpg"
    })
    
    import genlayer.gl as gl
    original_exec_prompt = getattr(gl.eq_principle, 'prompt_non_comparative', None)
    gl.eq_principle.prompt_non_comparative = lambda prompt, task, criteria: acceptance_json
    
    try:
        # Propose Offset
        with direct_vm.prank(direct_alice):
            direct_vm.value = 1 * 10**18
            contract.propose_offset("Billion Tree Tsunami", "Khyber Pakhtunkhwa", "Native regional trees", 1000000000, evidence_url)
        
        # Verify pending rewards
        alice_str = direct_alice.hex().lower()
        if not alice_str.startswith("0x"):
            alice_str = "0x" + alice_str
        assert int(contract.pending_rewards.get(alice_str, "0")) == 2 * 10**18
        
        # Withdraw rewards
        with direct_vm.prank(direct_alice):
            direct_vm.value = 0
            contract.withdraw_rewards()
            
        assert int(contract.pending_rewards.get(alice_str, "0")) == 0
        
        found_transfer = any("EthSend" in str(t) for t in direct_vm._traces)
        assert found_transfer, "Transfer trace missing"
        
    finally:
        if original_exec_prompt:
            gl.eq_principle.prompt_non_comparative = original_exec_prompt

@pytest.mark.direct
def test_real_burning_on_fraudulent_claim(direct_deploy, direct_vm, direct_alice):
    contract = direct_deploy("botanexa_contract.py")
    
    evidence_url = "https://en.wikipedia.org/wiki/Great_Green_Wall"
    direct_vm.mock_web(evidence_url, {"body": "Greenwasher fraud investigation...", "method": "GET", "status": 200})
    
    rejection_json = json.dumps({
        "is_accurate": False,
        "source_provenance_valid": False,
        "location_match": False,
        "species_safe": False,
        "tree_count_reasonable": False,
        "reasoning": "Rejected due to fraud",
        "carbon_sequestration_tons": "0",
        "ecological_suitability": "None",
        "ecological_role": "",
        "image_url": ""
    })
    
    import genlayer.gl as gl
    original_exec_prompt = getattr(gl.eq_principle, 'prompt_non_comparative', None)
    gl.eq_principle.prompt_non_comparative = lambda prompt, task, criteria: rejection_json
    
    try:
        with direct_vm.prank(direct_alice):
            direct_vm.value = 1 * 10**18
            contract.propose_offset("Fake Desert Trees", "0.0, 0.0", "Kudzu", 999999, evidence_url)
            
        alice_str = direct_alice.hex().lower()
        if not alice_str.startswith("0x"):
            alice_str = "0x" + alice_str
        assert int(contract.pending_rewards.get(alice_str, "0")) == 0
        
        found_burn = any("EthSend" in str(t) and "0000000000000000000000000000000000000000" in str(t) for t in direct_vm._traces)
        assert found_burn, "Burn trace missing"
        
    finally:
        if original_exec_prompt:
            gl.eq_principle.prompt_non_comparative = original_exec_prompt
