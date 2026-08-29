/* ===================================================
   BOTANEXA — Shared JavaScript Utilities
   GenLayer Studio Network Integration
   =================================================== */

// ── GenLayer Studio RPC Configuration ──
const GENLAYER_CONFIG = {
  chainId: '0xF22F',        // 61999 in hex
  chainIdDec: 61999,
  chainName: 'GenLayer Studio',
  rpcUrls: ['https://studio.genlayer.com/api'],
  nativeCurrency: {
    name: 'GEN',
    symbol: 'GEN',
    decimals: 18
  },
  blockExplorerUrls: []
};

// ── Deployed Contract Address on GenLayer Studio ──
// This address will be updated by the developer after deploying botanexa_contract.py on GenLayer Studio.
const CONTRACT_ADDRESS = '0x66D1Af5FeF41b6aF4D0CC088C43AD9bd9Ee5cAAc'; // Botanexa contract address

// ── Wallet State ──
window.botanexaWallet = {
  address: null,
  isConnected: false,
  chainId: null,
};

// ── Toast Notifications ──
function showToast(message, type = 'info', duration = 5000) {
  let toast = document.getElementById('botanexa-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'botanexa-toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }

  const icons = {
    success: '🌿',
    error: '❌',
    info: '🧪',
    warning: '⚠️'
  };

  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span style="font-size:1.2rem">${icons[type] || '🌱'}</span>
    <span>${message}</span>
  `;

  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => {
    toast.classList.remove('show');
  }, duration);
}

// ── Connect Wallet ──
async function connectWallet() {
  if (typeof window.ethereum === 'undefined') {
    showToast('MetaMask is required to connect to Botanexa.', 'error');
    window.open('https://metamask.io/', '_blank');
    return false;
  }

  try {
    showToast('Connecting to MetaMask...', 'info');

    const accounts = await window.ethereum.request({
      method: 'eth_requestAccounts'
    });

    if (!accounts || accounts.length === 0) {
      showToast('No accounts found. Please unlock MetaMask.', 'error');
      return false;
    }

    // Switch to GenLayer Studio Network
    await switchToGenLayer();

    window.botanexaWallet.address = accounts[0];
    window.botanexaWallet.isConnected = true;

    // Persist session
    localStorage.setItem('botanexa_wallet', accounts[0]);
    localStorage.setItem('botanexa_connected', 'true');

    updateWalletUI();
    showToast(`Wallet connected: ${shortenAddress(accounts[0])}`, 'success');

    // Attach listeners
    window.ethereum.on('accountsChanged', handleAccountsChanged);
    window.ethereum.on('chainChanged', handleChainChanged);

    return true;
  } catch (err) {
    if (err.code === 4001) {
      showToast('Connection request rejected by user.', 'warning');
    } else {
      showToast(`Connection error: ${err.message}`, 'error');
    }
    return false;
  }
}

// ── Switch/Register GenLayer Studio Network ──
async function switchToGenLayer() {
  try {
    await window.ethereum.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: GENLAYER_CONFIG.chainId }]
    });
  } catch (switchError) {
    // 4902 code indicates the chain is not added to Metamask
    if (switchError.code === 4902) {
      try {
        await window.ethereum.request({
          method: 'wallet_addEthereumChain',
          params: [GENLAYER_CONFIG]
        });
      } catch (addError) {
        showToast('Could not register GenLayer Studio network automatically. Please add it in MetaMask manually.', 'error');
        throw addError;
      }
    } else if (switchError.code === 4001) {
      showToast('GenLayer Studio network selection rejected.', 'warning');
      throw switchError;
    }
  }
}

// ── Disconnect Wallet ──
function disconnectWallet() {
  window.botanexaWallet = {
    address: null,
    isConnected: false,
    chainId: null,
  };

  localStorage.removeItem('botanexa_wallet');
  localStorage.removeItem('botanexa_connected');

  updateWalletUI();
  showToast('Wallet disconnected.', 'info');

  // Redirect to home if on staking page
  const protectedPages = ['propose.html'];
  const currentPage = window.location.pathname.split('/').pop();
  if (protectedPages.includes(currentPage)) {
    setTimeout(() => window.location.href = 'index.html', 1500);
  }
}

// ── MetaMask Event Handlers ──
function handleAccountsChanged(accounts) {
  if (accounts.length === 0) {
    disconnectWallet();
  } else if (accounts[0] !== window.botanexaWallet.address) {
    window.botanexaWallet.address = accounts[0];
    localStorage.setItem('botanexa_wallet', accounts[0]);
    updateWalletUI();
    showToast(`Account switched: ${shortenAddress(accounts[0])}`, 'info');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // Mobile Hamburger Toggle
  const hamburger = document.getElementById('hamburger');
  const navLinks = document.getElementById('nav-links');
  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      hamburger.classList.toggle('open');
      navLinks.classList.toggle('open');
    });
  }
});

function handleChainChanged(chainId) {
  window.botanexaWallet.chainId = chainId;
  if (chainId !== GENLAYER_CONFIG.chainId) {
    showToast('MetaMask switched away from GenLayer Studio. Please switch back to interact with Botanexa.', 'warning');
  }
}

// ── Restore Previous Session ──
async function restoreWalletSession() {
  if (typeof window.ethereum === 'undefined') return;
  if (localStorage.getItem('botanexa_connected') !== 'true') return;

  try {
    const accounts = await window.ethereum.request({ method: 'eth_accounts' });
    if (accounts.length > 0) {
      window.botanexaWallet.address = accounts[0];
      window.botanexaWallet.isConnected = true;
      updateWalletUI();
      window.ethereum.on('accountsChanged', handleAccountsChanged);
      window.ethereum.on('chainChanged', handleChainChanged);
    }
  } catch (err) {
    console.warn('Session restoration failed:', err);
  }
}

// ── Update Global Wallet UI Elements ──
async function updateWalletUI() {
  const connectBtn = document.getElementById('connect-wallet-btn');
  const walletInfo = document.getElementById('wallet-info-bar');
  const walletAddrEl = document.getElementById('wallet-address-display');
  const walletBalEl = document.getElementById('wallet-balance-display');

  if (window.botanexaWallet.isConnected && window.botanexaWallet.address) {
    if (connectBtn) connectBtn.style.display = 'none';
    if (walletInfo) walletInfo.style.display = 'flex';
    if (walletAddrEl) walletAddrEl.textContent = shortenAddress(window.botanexaWallet.address);
    if (walletBalEl && window.getNativeBalance) {
      try {
        const bal = await window.getNativeBalance(window.botanexaWallet.address);
        walletBalEl.textContent = `${bal} GEN`;
      } catch (e) {
        walletBalEl.textContent = '';
      }
    }
  } else {
    if (connectBtn) connectBtn.style.display = 'flex';
    if (walletInfo) walletInfo.style.display = 'none';
    if (walletBalEl) walletBalEl.textContent = '';
  }
}

// ── Address Shortener Helper ──
function shortenAddress(addr) {
  if (!addr) return '';
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
}

// ── Leaf Particle Generator (Visual Effect) ──
function initLeafParticles(containerId, count = 20) {
  const container = document.getElementById(containerId);
  if (!container) return;

  for (let i = 0; i < count; i++) {
    const leaf = document.createElement('div');
    leaf.className = 'leaf';

    const size = Math.random() * 15 + 8; // Leaf dimensions
    const left = Math.random() * 100;
    const duration = Math.random() * 12 + 10; // Floating speed
    const delay = Math.random() * 15;
    const opacity = Math.random() * 0.4 + 0.1;

    leaf.style.cssText = `
      width: ${size}px;
      height: ${size * 1.5}px;
      left: ${left}%;
      animation-duration: ${duration}s;
      animation-delay: -${delay}s;
      opacity: ${opacity};
    `;

    container.appendChild(leaf);
  }
}

// ── Sleep Utility Helper ──
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Shared Initialization on DOM Load ──
document.addEventListener('DOMContentLoaded', async () => {
  initLeafParticles('particle-field', 20);
  await restoreWalletSession();

  const connectBtn = document.getElementById('connect-wallet-btn');
  if (connectBtn) {
    connectBtn.addEventListener('click', connectWallet);
  }

  const disconnectBtn = document.getElementById('disconnect-btn');
  if (disconnectBtn) {
    disconnectBtn.addEventListener('click', disconnectWallet);
  }

  // Scroll navbar animation
  const navbar = document.getElementById('navbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 30) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
    });
  }
});
