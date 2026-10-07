# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import json

class BotanexaRegistry(gl.Contract):
    """
    BOTANEXA: Decentralized AI-powered reforestation and carbon offset audit registry.

    ECONOMIC MODEL:
    - Staking requirement: 1 GEN per project audit proposal.
    - VERIFIED  -> Proposer earns 2 GEN (1 GEN stake returned + 1 GEN reward).
    - REJECTED  -> 1 GEN stake is burned to null address.
    """

    # ── Storage ───────────────────────────────────────────────────
    query_history:        TreeMap[str, str]   # lower(address)      -> JSON history list
    verified_projects:    TreeMap[str, str]   # lower(project_name) -> JSON project data
    pending_rewards:      TreeMap[str, str]   # lower(address)      -> wei amount string
    total_pending_rewards: u256                # Tracks global outstanding reward obligations
    total_queries:        u256
    total_trees_audited:  u256
    total_staked_amount:  u256
    total_co2_offset:     u256
    recent_projects_list: str                 # JSON list of recently verified project names

    def __init__(self):
        self.query_history = TreeMap()
        self.verified_projects = TreeMap()
        self.pending_rewards = TreeMap()
        self.total_pending_rewards = 0
        self.total_queries = u256(0)
        self.total_trees_audited = u256(0)
        self.total_staked_amount = u256(0)
        self.total_co2_offset = u256(0)
        self.recent_projects_list = "[]"

    # ── Core Staking + AI Validation ─────────────────────────────

    @gl.public.write.payable
    def fund_treasury(self) -> None:
        """Allow anyone (or the owner) to deposit GEN into the reward treasury."""
        pass

    @gl.public.write.payable
    def propose_offset(self, project_name: str, location_coords: str, species_planted: str, tree_count: int, evidence_url: str) -> None:
        caller    = gl.message.sender_address
        stake     = gl.message.value
        ONE_GEN   = u256(1000000000000000000)      # 1e18 wei

        caller = gl.message.sender_address
        stake = gl.message.value
        ONE_GEN = u256(10**18)
        
        # Harden Input Validation
        if stake < ONE_GEN:
            raise gl.vm.UserError("Must stake at least 1 GEN to propose a project audit.")
        if not evidence_url.startswith("http"):
            raise gl.vm.UserError("Invalid evidence_url. Must start with http or https.")
        if int(tree_count) <= 0:
            raise gl.vm.UserError("Tree count must be greater than 0.")

        project_clean = project_name.strip()
        project_lower = project_clean.lower()

        if len(project_clean) > 100:
            raise gl.vm.UserError("Project name too long.")

        if not project_lower:
            raise gl.vm.UserError("Project name cannot be empty.")

        if project_lower in self.verified_projects:
            raise gl.vm.UserError(
                f"Project '{project_clean}' is already verified in the Botanexa registry. "
                "Verify a new project to earn a reward."
            )

        # Check if contract has enough native funds to back the reward obligation
        if self.balance < self.total_pending_rewards + stake + ONE_GEN:
            raise gl.vm.UserError("Contract does not have enough treasury funds to back this reward bonus.")

        self.total_staked_amount = self.total_staked_amount + stake
        self.total_trees_audited = self.total_trees_audited + u256(int(tree_count))

        def build_prompt() -> str:
            # Fetch and render the actual web content inside the non-deterministic block.
            web_data = gl.nondet.web.render(evidence_url, mode="text")

            return f"""You are a STRICT auditor for Botanexa, a decentralized carbon offset registry.
Your job is to REJECT fraudulent or unverified afforestation/reforestation claims based on the provided evidence URL.

--- PROPOSED CLAIM ---
Project / Source: {project_clean}
Location (Lat/Long): {location_coords}
Species Planted: {species_planted}
Tree Count: {tree_count}
Evidence URL: {evidence_url}

--- EVIDENCE EXTRACTED ---
{web_data[:4000]}  # Limiting context to avoid token overflow

--- INSTRUCTIONS ---
STEP 1 - Source Authority Check: Determine if the evidence URL belongs to an independent, authenticated, and globally recognized authority.
STEP 2 - Read the evidence webpage content carefully.
STEP 3 - Compare the proposed coordinates, tree count, and species against the source text.
STEP 4 - Calculate estimated carbon sequestration (assuming ~0.1 to 1 ton per tree) and assess ecological suitability.
STEP 5 - Apply the REJECTION RULES below.

MANDATORY REJECTION RULES (set is_accurate=false if ANY of these apply):
- SOURCE PROVENANCE FAILED: If the URL appears to be a claimant-controlled domain, a personal blog, a generic corporate PR page, or any unverified/suspicious source, you MUST reject the claim immediately.
- The evidence URL does NOT mention the project "{project_clean}" or the specified location/work.
- The tree count claimed ({tree_count}) is significantly higher (over 20% inflation) than what is documented in the source.
- The planted species include highly invasive species for that region. (NOTE: If the claimed species is generic, like 'Native trees', and the source text does not explicitly contradict it, you MUST assume the species is safe).
- The evidence webpage indicates the project was completely cancelled, abandoned, or proven to be a total hoax.
- The coordinates placed ("{location_coords}") are completely unrelated to the project location described in the source.

Return ONLY a valid JSON object (no markdown, no backticks, no extra text):
{{
  "is_accurate": true or false,
  "source_provenance_valid": true or false,
  "location_match": true or false,
  "species_safe": true or false,
  "tree_count_reasonable": true or false,
  "carbon_sequestration_tons": 500.0,
  "ecological_suitability": "Short assessment of species suitability for region",
  "ecological_role": "Primary role, e.g. soil stabilization",
  "reasoning": "Explain step-by-step why you accepted or rejected this.",
  "image_url": "If accepted, extract a direct absolute image URL (starting with https://). Otherwise empty."
}}
"""

        # Use prompt_non_comparative so validators reach consensus independently
        result_str = gl.eq_principle.prompt_non_comparative(
            build_prompt,
            task="Verify the proposed afforestation project and evaluate its claims.",
            criteria=(
                "The leader's response MUST be a valid JSON object containing is_accurate, reasoning, "
                "carbon_sequestration_tons, ecological_role, and ecological_suitability. "
                "The 'is_accurate' field MUST be false if the evidence URL does not support the location, tree count, or species, "
                "or if the species are highly invasive. If the claimed species is generic (like 'Native trees') and the source text "
                "does not explicitly contradict it, the leader MUST assume the species is safe. "
                "The 'carbon_sequestration_tons' MUST be mathematically reasonable based on a ~0.1 to 1.0 ton per tree estimate."
            )
        )

        try:
            c = result_str.strip()
            s = c.find("{"); e = c.rfind("}") + 1
            if s != -1 and e != 0:
                c = c[s:e]
            import json
            data = json.loads(c)
            result_dict = {
                "is_accurate": bool(data.get("is_accurate")),
                "source_provenance_valid": bool(data.get("source_provenance_valid")),
                "location_match": bool(data.get("location_match")),
                "species_safe": bool(data.get("species_safe")),
                "tree_count_reasonable": bool(data.get("tree_count_reasonable")),
                "carbon_sequestration_tons": str(data.get("carbon_sequestration_tons", "0.0")),
                "ecological_suitability": str(data.get("ecological_suitability", "Unverified")),
                "ecological_role": str(data.get("ecological_role", "")),
                "reasoning": str(data.get("reasoning", "No reasoning provided.")),
                "image_url": str(data.get("image_url", ""))
            }
        except Exception:
            result_dict = {"is_accurate": False, "source_provenance_valid": False, "location_match": False, "species_safe": False, "tree_count_reasonable": False, "reasoning": "Failed to parse LLM JSON output.", "carbon_sequestration_tons": "0", "ecological_suitability": "Unverified", "ecological_role": "", "image_url": ""}
        is_accurate = result_dict["is_accurate"]

        safe_exp = {
            "project_name":           project_clean,
            "location_coords":        location_coords,
            "species_planted":        [species_planted] if isinstance(species_planted, str) else species_planted,
            "tree_count":             int(tree_count),
            "carbon_offset_tons":     result_dict.get("carbon_sequestration_tons", "0.0"),
            "ecological_suitability": result_dict.get("ecological_suitability", "Unverified"),
            "ecological_role":        result_dict.get("ecological_role", ""),
            "reasoning":              result_dict.get("reasoning", "No reasoning provided."),
            "image_url":              result_dict.get("image_url", ""),
            "key_facts":              [],
            "companion_species":      [],
            "visualization_type":     "forest_density",
            "colors":                 { "primary": "#00dc64", "secondary": "#b8ffd1", "glow": "#00ff73" }
        }

        caller_str = self._get_addr_str(caller)

        if is_accurate:
            # ── ACCEPTED: Reward bonus is strictly capped at 1 GEN (stake returned + 1 GEN reward = 2 GEN) ──
            reward_bonus = ONE_GEN
            reward_wei = stake + reward_bonus
            
            # Track the reward for the user to pull later
            current = u256(int(self.pending_rewards.get(caller_str, "0")))
            self.pending_rewards[caller_str] = str(int(current + reward_wei))
            
            # Update total pending rewards
            self.total_pending_rewards = self.total_pending_rewards + reward_wei

            # Cache the successful result
            self.verified_projects[project_lower] = json.dumps({
                "explanation":        safe_exp,
                "validator_consensus": True,
                "proposer":           caller_str,
            })

            # Update global stats
            try:
                self.total_co2_offset = self.total_co2_offset + u256(int(float(safe_exp["carbon_offset_tons"])))
            except Exception:
                pass

            # Update the recent projects list
            try:
                pop = json.loads(self.recent_projects_list)
                if not isinstance(pop, list): pop = []
            except Exception:
                pop = []
            if project_clean not in pop:
                pop.append(project_clean)
                if len(pop) > 50:
                    pop = pop[-50:]
                self.recent_projects_list = json.dumps(pop)

            # Inline record history (ACCEPTED)
            try:
                hist = json.loads(self.query_history[caller_str]) if caller_str in self.query_history else []
                if not isinstance(hist, list): hist = []
            except Exception:
                hist = []
            hist.append({"project": project_clean, "project_lower": project_lower,
                         "reasoning": safe_exp.get("reasoning", ""), 
                         "image_url": safe_exp.get("image_url", ""),
                         "accepted": True})
            if len(hist) > 50: hist = hist[-50:]
            self.query_history[caller_str] = json.dumps(hist)
        else:
            # ── REJECTED: Burn the stake to the null address ──
            _Recipient(Address("0x0000000000000000000000000000000000000000")).emit_transfer(value=stake)
            
            # Inline record history (REJECTED)
            try:
                hist = json.loads(self.query_history[caller_str]) if caller_str in self.query_history else []
                if not isinstance(hist, list): hist = []
            except Exception:
                hist = []
            hist.append({"project": project_clean, "project_lower": project_lower,
                         "reasoning": result_dict.get("reasoning", "Audit evidence did not support coordinates, tree counts, or species safety."), "accepted": False})
            if len(hist) > 50: hist = hist[-50:]
            self.query_history[caller_str] = json.dumps(hist)

        self.total_queries = self.total_queries + u256(1)

    # ── View: pending reward balance ─────────────────────────────

    def _get_addr_str(self, addr_obj) -> str:
        s = str(addr_obj).lower()
        if "0x" in s:
            s = "0x" + s.split("0x")[1].split(">")[0].strip()
        return s

    @gl.public.view
    def get_pending_reward(self, user_address: str) -> str:
        key = user_address.strip().lower()
        return self.pending_rewards[key] if key in self.pending_rewards else "0"

    # ── Write: Withdraw Rewards (Deterministic) ──────────────────

    @gl.public.write
    def withdraw_rewards(self) -> None:
        """Withdraws accumulated rewards for the caller."""
        caller = gl.message.sender_address
        caller_str = self._get_addr_str(caller)
        
        pending_str = self.pending_rewards.get(caller_str, "0")
        pending_amount = u256(int(pending_str))
        
        if pending_amount == u256(0):
            raise gl.vm.UserError("No rewards available to withdraw.")
            
        # Zero the balance first (Checks-Effects-Interactions pattern)
        self.pending_rewards[caller_str] = "0"
        
        # Deduct from total pending rewards
        self.total_pending_rewards = self.total_pending_rewards - pending_amount
        
        # Emit the native transfer to the EOA
        _Recipient(Address(caller_str)).emit_transfer(value=pending_amount)

    @gl.public.view
    def get_cached_offset(self, project_name: str) -> str:
        k = project_name.strip().lower()
        return self.verified_projects[k] if k in self.verified_projects else json.dumps({"found": False})

    @gl.public.view
    def get_user_history(self, user_address: str) -> str:
        k = user_address.strip().lower()
        return self.query_history[k] if k in self.query_history else "[]"

    @gl.public.view
    def get_proposal_status(self, user_address: str, project_name: str) -> str:
        k = user_address.strip().lower()
        pl = project_name.strip().lower()
        if k in self.query_history:
            try:
                hist = json.loads(self.query_history[k])
                for e in reversed(hist):
                    if e.get("project_lower") == pl:
                        if e.get("accepted"):
                            return json.dumps({"status": "ACCEPTED",
                                               "reasoning": e.get("reasoning", ""),
                                               "image_url": e.get("image_url", ""),
                                               "reward": 2})
                        return json.dumps({"status": "REJECTED",
                                           "reasoning": e.get("reasoning", ""),
                                           "reward": 0})
            except Exception:
                pass
        return json.dumps({"status": "PENDING", "reasoning": "Not yet processed.", "reward": 0})

    @gl.public.view
    def get_stats(self) -> str:
        return json.dumps({
            "total_queries": int(self.total_queries),
            "total_trees_audited": int(self.total_trees_audited),
            "total_staked_amount": str(self.total_staked_amount),
            "total_co2_offset": int(self.total_co2_offset),
            "platform": "BOTANEXA",
            "network": "GenLayer Studio"
        })

    @gl.public.view
    def get_recent_projects(self) -> str:
        return self.recent_projects_list

@gl.evm.contract_interface
class _Recipient:
    class View:
        pass
    class Write:
        pass
