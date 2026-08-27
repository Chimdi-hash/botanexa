# Botanexa 🌿
> **Decentralized Reforestation & Carbon Offset Audit Registry**
> Built on the GenLayer Studio Network

Botanexa is a decentralized, on-chain registry that audits and certifies corporate reforestation and carbon offset claims. By combining economic staking with GenLayer's AI-native consensus mechanism, Botanexa resolves the rampant trust deficit, greenwashing, and double-counting issues currently undermining the voluntary carbon markets.

---

## 🛡️ The Trust Problem Solved

Carbon offsets are crucial for environmental sustainability, but the current verification market faces massive trust gaps:
1. **Greenwashing:** Corporations publish falsified or highly inflated tree planting reports to claim carbon neutrality or green tax credits.
2. **Centralized Collusion:** Carbon credit auditors are centralized, expensive, and subject to conflict of interest or database tampering.
3. **Ecological Damage:** Projects sometimes plant non-native or invasive species that devastate local water tables and biodiversity, passing them off as "reforestation."

### The Botanexa Solution
Botanexa turns environmental verification into a crypto-economically secure game:
* **Economic Collateral:** Proposers must stake **1 GEN** to register a project.
* **Decentralized AI Auditing:** Rather than relying on a single centralized agency, GenLayer **AI-consensus validators** automatically scrape project audit URLs, cross-reference coordinates against mapping data, check if the planted species are invasive/inappropriate for that region, and calculate realistic annual carbon sequestration capacities.
* **Optimistic Democracy:** The network reaches consensus using the **Equivalence Principle**. If a project is verified, the proposer is rewarded with **2 GEN** (returned stake + reward). If the report is fraudulent or greenwashed, the stake is burned (sent to the null address), creating an immediate financial penalty for greenwashing.

---

## ⚙️ Architecture & Technology

### 1. The Intelligent Contract (`botanexa_contract.py`)
Written in Python for GenVM, the contract is fully stateful, using `TreeMap` structures to keep records of:
* Verified projects (caching coordinate, species, tree count, carbon tons, and consensus reasoning data).
* Proposal statuses (PENDING, ACCEPTED, REJECTED).
* Claimable user rewards (using the Checks-Effects-Interactions pattern for secure native balance withdrawals).
* Staking and burning mechanics utilizing `_Recipient.emit_transfer`.

### 2. Frontend Wallet & Lifecycle Handler (`app.js`, `propose.html`)
The frontend connects directly to MetaMask and interfaces with the GenLayer Studio JSON-RPC:
* **Pre-Check Phase:** Before submitting a transaction, the frontend queries the contract via a free read-only view call to check if the project is already verified, saving gas and GEN.
* **Staking Transaction:** Builds and signs the transaction in MetaMask, transferring 1 GEN to the contract.
* **High-Fidelity Lifecycle Tracker:** GenLayer transactions take 30-90 seconds because AI validators must fetch live web data. The UI tracks the transaction status dynamically through 5 stages:
  1. *Sign:* Approve MetaMask prompt.
  2. *Broadcast:* Broadcasting tx to the RPC network.
  3. *AI Audit:* Validators fetching and parsing the evidence webpage.
  4. *Consensus:* Validator nodes voting on the Leader's proposal.
  5. *Verified/Slashed:* Committing the verified state or burning the stake.

### 3. Generative Forest Visualizer (`registry.html`)
Every verified forest displays a unique generative 2D HTML Canvas art. The system reads on-chain metadata and dynamically generates trees:
* Density (tree count) corresponds to the verified tree count.
* Species coloring and shapes are rendered based on the botanical family classification and ecological suitability verified by the AI.

---

## 🚀 How to Run and Deploy

### Prerequisites
* **MetaMask Extension** installed in your browser.
* **Node.js** (v16+) installed.

### 1. Configure MetaMask
Add the **GenLayer Studio** network to MetaMask:
* **Network Name:** GenLayer Studio
* **New RPC URL:** `https://studio.genlayer.com/api`
* **Chain ID:** `61999` (Hex: `0xF22F`)
* **Currency Symbol:** `GEN`

*(Note: The DApp will also prompt you to add/switch to this network automatically when you connect your wallet).*

### 2. Deploy the Intelligent Contract
1. Open the [GenLayer Studio](https://studio.genlayer.com).
2. Create a new file named `botanexa_contract.py` and paste the contents of `botanexa_contract.py`.
3. Select the contract and click **Deploy**.
4. Copy the deployed contract address and paste it into the `CONTRACT_ADDRESS` constant at the top of `app.js`:
   ```javascript
   const CONTRACT_ADDRESS = 'YOUR_DEPLOYED_CONTRACT_ADDRESS';
   ```

### 3. Run the Frontend Locally
Install server dependencies and run the local server:
```bash
# Navigate to the project directory
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

### 4. Build/Bundle the SDK (Optional Developer Step)
To regenerate `genlayer_bundle.js` from `temp_genlayer/wrapper.js` (which bundles the SDK and Viem):
```bash
cd temp_genlayer
npm install
npm run build
```

---

## 🌐 Deploying to Vercel

Botanexa is fully optimized for Vercel. SPA paths and static assets are mapped using the `vercel.json` file. To deploy:
```bash
# Deploy to Vercel (Production)
npx vercel --prod
```
The site will compile and deploy as a high-speed, secure static site with appropriate HTTP headers and SEO clean paths.
