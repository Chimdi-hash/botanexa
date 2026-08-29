# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
# Botanexa Carbon Offset & Reforestation Audit Registry
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
    recent_projects_list: str                 # JSON list of recently verified project names

    def __init__(self):
        self.query_history = TreeMap()
        self.verified_projects = TreeMap()
        self.pending_rewards = TreeMap()
        self.total_pending_rewards = 0
        self.total_queries = 0
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

        if stake < ONE_GEN:
            raise gl.vm.UserError("Must stake at least 1 GEN to propose a project audit.")

        project_clean = project_name.strip()
        project_lower = project_clean.lower()

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

        # ── AI Validation Prompt Block ──
        def get_web_and_prompt() -> str:
            # Fetch webpage inside non-deterministic block
            response = gl.nondet.web.get(evidence_url)
            web_data = response.body.decode("utf-8", errors="ignore")
            
            return f"""You are a STRICT ecological fact-checker for the BOTANEXA reforestation and carbon offset audit registry.
Your job is to REJECT incorrect, inflated, or greenwashed claims. Be extremely critical of corporate ecological reports.

Project Name claimed: "{project_clean}"
Stated GPS/Location: "{location_coords}"
Declared Species: "{species_planted}"
Declared Tree Count: {tree_count}
Evidence URL: "{evidence_url}"

--- EVIDENCE WEBPAGE CONTENT ---
{web_data}
--------------------------------

STEP 1 — Read the evidence webpage content carefully.
STEP 2 — Find references to "{project_clean}" or reforestation projects in that location.
STEP 3 — Compare the proposed coordinates, tree count, and species against the source text.
STEP 4 — Apply the REJECTION RULES below.

MANDATORY REJECTION RULES (set is_accurate=false if ANY of these apply):
- The evidence URL does NOT mention the project "{project_clean}" or the specified location/work.
- The tree count claimed ({tree_count}) is significantly higher (over 20% inflation) than what is documented in the source.
- The planted species include highly invasive species for that region (e.g. planting Kudzu, Water Hyacinth, Japanese Knotweed, or species banned by regional forestry guidelines).
- The evidence webpage indicates the project has been cancelled, abandoned, or exposed as fraudulent.
- The coordinates placed ("{location_coords}") are completely unrelated to the project location described in the source.
- The evidence URL is not functional or does not contain relevant environmental/botanical reporting.

CARBON OFFSET ESTIMATE RULES:
- A mature native tree typically sequesters approximately 22kg (0.022 metric tons) of CO2 per year.
- Calculate: tree_count * 0.022 = carbon_offset_tons. 
- Adjust this value down if the source reports that the trees are saplings, newly planted, or if they are slow-growing species.
- Provide the final calculated carbon_offset_tons as a string formatted number (e.g. "110.0") in the JSON response.

Return ONLY a valid JSON object (no markdown, no backticks, no extra text):
{{
    "is_accurate": false,
    "reasoning": "The evidence URL states that the project only planted [quote exact tree count or species from source]. The proposed submission claims {tree_count} trees which contradicts the source by [explain discrepancy]. Therefore, this claim is rejected as inaccurate.",
    "project_name": "{project_clean}",
    "location_coords": "{location_coords}",
    "species_planted": ["Tree species list matching source"],
    "tree_count": 0,
    "carbon_offset_tons": "0.0",
    "ecological_suitability": "Unsuitable - Invasive / Contradicted Species",
    "ecological_role": "None - rejected",
    "key_facts": [],
    "companion_species": []
}}

If the project is fully accurate, return:
{{
    "is_accurate": true,
    "reasoning": "The evidence URL confirms that the project '{project_clean}' planted {tree_count} trees of species [name species] at the specified location. Coordinates match local records.",
    "project_name": "{project_clean}",
    "location_coords": "{location_coords}",
    "species_planted": ["Scientific/common names of species"],
    "tree_count": {tree_count},
    "carbon_offset_tons": "0.0",
    "ecological_suitability": "Highly Suitable - Native Species",
    "ecological_role": "Provides soil stabilization, enhances local biodiversity, and restores natural water retention in the local watershed.",
    "key_facts": ["Fact 1 from report", "Fact 2 from report"],
    "companion_species": ["Species 1", "Species 2"]
}}"""

        task = "Verify the reforestation and carbon offset claims using the provided evidence URL."
        criteria = (
            "The leader's response must be a valid JSON object containing 'is_accurate' and 'reasoning'. "
            "CRITICAL: The 'is_accurate' field MUST be false if the tree counts are inflated, the species are invasive, "
            "or the coordinates do not match the report. 'is_accurate' can only be true if the project details "
            "align perfectly with the facts in the evidence URL. Reject greenwashed or unsupported claims."
        )

        result_str = gl.eq_principle.prompt_non_comparative(
            input=get_web_and_prompt,
            task=task,
            criteria=criteria,
        )

        # ── Parse AI output ──
        try:
            cleaned = result_str.strip()
            if "```" in cleaned:
                s = cleaned.find("{"); e = cleaned.rfind("}") + 1
                if s >= 0 and e > s:
                    cleaned = cleaned[s:e]
            data = json.loads(cleaned)
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}

        is_accurate = bool(data.get("is_accurate", False))

        safe_exp = {
            "project_name":           data.get("project_name",           project_clean),
            "location_coords":        data.get("location_coords",        location_coords),
            "species_planted":        data.get("species_planted",        [species_planted] if isinstance(species_planted, str) else species_planted),
            "tree_count":             int(data.get("tree_count",         tree_count)),
            "carbon_offset_tons":     str(data.get("carbon_offset_tons", "0.0")),
            "ecological_suitability": data.get("ecological_suitability", "Unverified"),
            "ecological_role":        data.get("ecological_role",        ""),
            "reasoning":              data.get("reasoning",              ""),
            "key_facts":              data.get("key_facts",              []) if isinstance(data.get("key_facts"),    list) else [],
            "companion_species":      data.get("companion_species",      []) if isinstance(data.get("companion_species"), list) else [],
            "visualization_type":     "forest_density",
            "colors":                 { "primary": "#00dc64", "secondary": "#b8ffd1", "glow": "#00ff73" }
        }

        caller_str = str(caller).lower()

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
                         "reasoning": safe_exp.get("reasoning", ""), "accepted": True})
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
                         "reasoning": data.get("reasoning", "Audit evidence did not support coordinates, tree counts, or species safety."), "accepted": False})
            if len(hist) > 50: hist = hist[-50:]
            self.query_history[caller_str] = json.dumps(hist)

        self.total_queries = self.total_queries + u256(1)

    # ── View: pending reward balance ─────────────────────────────

    @gl.public.view
    def get_pending_reward(self, user_address: str) -> str:
        key = user_address.strip().lower()
        return self.pending_rewards[key] if key in self.pending_rewards else "0"

    # ── Write: Withdraw Rewards (Deterministic) ──────────────────

    @gl.public.write
    def withdraw_rewards(self) -> None:
        """Withdraws accumulated rewards for the caller."""
        caller = gl.message.sender_address
        caller_str = str(caller).lower()
        
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
