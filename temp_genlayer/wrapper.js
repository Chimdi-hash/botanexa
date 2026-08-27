import { createClient } from 'genlayer-js';
import { studionet } from 'genlayer-js/chains';
import { custom } from 'viem';

const GENLAYER_RPC = 'https://studio.genlayer.com/api';

// ── Write a state-changing transaction ──
window.callGenLayer = async function(contract, method, args, accountAddress, value) {
  if (!accountAddress) throw new Error('Account address is missing');
  const client = createClient({ chain: studionet, transport: custom(window.ethereum) });
  const txArgs = {
    address: contract,
    functionName: method,
    args: args,
    account: { address: accountAddress }
  };
  if (value) { txArgs.value = BigInt(value); }
  const txHash = await client.writeContract(txArgs);
  return txHash;
};

// ── Read contract state ──
window.readGenLayer = async function(contract, method, args) {
  const client = createClient({ chain: studionet, transport: window.ethereum ? custom(window.ethereum) : undefined });
  const request = { address: contract, functionName: method };
  if (args !== undefined && args !== null) { request.args = args; }
  return await client.readContract(request);
};

// ── Get native GEN balance ──
window.getNativeBalance = async function(address) {
  const client = createClient({ chain: studionet, transport: window.ethereum ? custom(window.ethereum) : undefined });
  const balance = await client.getBalance({ address });
  return (Number(balance) / 1e18).toFixed(4);
};

// ── Poll tx status via eth_getTransactionByHash (GenLayer-specific) ──
window.getGenLayerTxStatus = async function(txHash) {
  try {
    const resp = await fetch(GENLAYER_RPC, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'eth_getTransactionByHash',
        params: [txHash],
        id: 1
      })
    });
    const data = await resp.json();
    if (!data.result) return { isFinalized: false, isSuccess: false, isError: false };

    const tx = data.result;
    const statusChanges  = tx.current_status_changes || [];
    const monitoring     = tx.current_monitoring    || {};
    const resultName     = tx.result_name           || '';
    const status         = (tx.status               || '').toUpperCase();

    // GenLayer uses various terminal state names — treat all as "finalized"
    const TERMINAL = ['FINALIZED', 'ACCEPTED', 'CANCELLED', 'UNDETERMINED'];
    const isFinalized =
      TERMINAL.some(s => statusChanges.includes(s)) ||
      TERMINAL.some(s => s in monitoring)           ||
      resultName !== ''                              ||
      TERMINAL.includes(status);

    // GenVM execution result from the first validator
    let executionResult = 'PENDING';
    try {
      const validators = tx.consensus_data?.validators || [];
      if (validators.length > 0) {
        executionResult = validators[0]?.execution_result ||
                          validators[0]?.genvm_result?.execution_result || 'PENDING';
      }
    } catch(e) {}

    return {
      isFinalized,
      isSuccess: isFinalized && executionResult !== 'ERROR',
      isError:   isFinalized && executionResult === 'ERROR',
      resultName,
      status,
    };
  } catch(e) {
    console.error("Tx poll RPC error:", e);
    return { isFinalized: false, isSuccess: false, isError: false, error: e.message };
  }
};
