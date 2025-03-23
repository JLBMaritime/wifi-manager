document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const connectionDetails = document.getElementById('connection-details');
    const networksList = document.getElementById('networks-list');
    const savedList = document.getElementById('saved-list');
    const diagnosticsResults = document.getElementById('diagnostics-results');
    const scanButton = document.getElementById('scan-button');
    const pingButton = document.getElementById('ping-button');
    const pingTarget = document.getElementById('ping-target');
    const pingResults = document.getElementById('ping-results');
    const pingOutput = document.getElementById('ping-output');
    const passwordModal = document.getElementById('password-modal');
    const modalNetworkName = document.getElementById('modal-network-name');
    const passwordForm = document.getElementById('password-form');
    const passwordInput = document.getElementById('password');
    const showPasswordCheckbox = document.getElementById('show-password');
    const closeButton = document.querySelector('.close-button');
    const toastContainer = document.getElementById('toast-container');

    // State
    let currentNetwork = null;
    let selectedNetwork = null;
    let refreshInterval = null;

    // Initialize
    init();

    function init() {
        // Set up event listeners
        scanButton.addEventListener('click', scanNetworks);
        pingButton.addEventListener('click', runPingTest);
        closeButton.addEventListener('click', closeModal);
        passwordForm.addEventListener('submit', connectWithPassword);
        showPasswordCheckbox.addEventListener('change', togglePasswordVisibility);
        
        // Initial data load
        loadCurrentConnection();
        loadSavedNetworks();
        scanNetworks();
        loadDiagnostics();
        
        // Set up refresh interval (every 15 seconds)
        refreshInterval = setInterval(() => {
            loadCurrentConnection();
            loadSavedNetworks();
            loadDiagnostics();
            // Refresh scan results every minute (less frequently)
            if (new Date().getSeconds() < 15) {
                scanNetworks();
            }
        }, 15000);
    }
    
    // Toggle password visibility
    function togglePasswordVisibility() {
        passwordInput.type = showPasswordCheckbox.checked ? 'text' : 'password';
    }

    // API Functions
    async function fetchAPI(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            if (data) {
                options.body = JSON.stringify(data);
            }
            
            const response = await fetch(`/api/${endpoint}`, options);
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            showToast('Error communicating with server', 'error');
            return null;
        }
    }

    async function loadCurrentConnection() {
        // Don't show loading indicator if we already have data
        if (!currentNetwork) {
            connectionDetails.innerHTML = '<div class="loading">Loading...</div>';
        }
        
        const data = await fetchAPI('current');
        if (!data) return;
        
        currentNetwork = data;
        
        if (data.ssid) {
            connectionDetails.innerHTML = `
                <div class="connection-info">
                    <div class="connection-label">Network:</div>
                    <div class="connection-value">${data.ssid}</div>
                    
                    <div class="connection-label">IP Address:</div>
                    <div class="connection-value">${data.ip_address || 'Not available'}</div>
                    
                    <div class="connection-label">Signal Strength:</div>
                    <div class="connection-value">${data.signal_strength || 'Not available'}</div>
                </div>
            `;
        } else {
            connectionDetails.innerHTML = `
                <div class="no-connection">
                    <p>Not connected to any network</p>
                </div>
            `;
        }
    }

    async function scanNetworks() {
        scanButton.disabled = true;
        scanButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
        networksList.innerHTML = '<div class="loading">Scanning...</div>';
        
        const data = await fetchAPI('scan');
        
        scanButton.disabled = false;
        scanButton.innerHTML = '<i class="fas fa-sync-alt"></i> Scan';
        
        if (!data) return;
        
        if (data.length === 0) {
            networksList.innerHTML = '<p class="text-center">No networks found</p>';
            return;
        }
        
        // Sort networks by signal strength (descending)
        data.sort((a, b) => {
            const signalA = parseInt(a.signal_strength) || 0;
            const signalB = parseInt(b.signal_strength) || 0;
            return signalB - signalA;
        });
        
        let html = '';
        
        data.forEach(network => {
            const signalClass = getSignalClass(network.signal_strength);
            const isConnected = currentNetwork && currentNetwork.ssid === network.ssid;
            
            html += `
                <div class="network-item">
                    <div class="network-info">
                        <div class="network-name">
                            <div class="signal-strength ${signalClass}">
                                <div class="signal-bar bar-1"></div>
                                <div class="signal-bar bar-2"></div>
                                <div class="signal-bar bar-3"></div>
                                <div class="signal-bar bar-4"></div>
                            </div>
                            ${network.ssid} ${isConnected ? '<span style="color: var(--success-color)">(Connected)</span>' : ''}
                        </div>
                        <div class="network-details">
                            Signal: ${network.signal_strength || 'Unknown'} | Security: ${network.security || 'Unknown'}
                        </div>
                    </div>
                    <div class="network-actions">
                        ${!isConnected ? `<button class="action-button connect-btn" data-ssid="${network.ssid}" data-security="${network.security}">
                            <i class="fas fa-wifi"></i> Connect
                        </button>` : ''}
                    </div>
                </div>
            `;
        });
        
        networksList.innerHTML = html;
        
        // Add event listeners to connect buttons
        document.querySelectorAll('.connect-btn').forEach(button => {
            button.addEventListener('click', function() {
                const ssid = this.getAttribute('data-ssid');
                const security = this.getAttribute('data-security');
                
                if (security === 'Open') {
                    connectToNetwork(ssid, null, 'Open');
                } else {
                    showPasswordModal(ssid);
                }
            });
        });
    }

    async function loadSavedNetworks() {
        savedList.innerHTML = '<div class="loading">Loading...</div>';
        
        const data = await fetchAPI('saved');
        if (!data) return;
        
        if (data.length === 0) {
            savedList.innerHTML = '<p class="text-center">No saved networks</p>';
            return;
        }
        
        let html = '';
        
        data.forEach(network => {
            const isConnected = currentNetwork && currentNetwork.ssid === network.ssid;
            
            html += `
                <div class="network-item">
                    <div class="network-info">
                        <div class="network-name">
                            ${network.ssid} ${isConnected ? '<span style="color: var(--success-color)">(Connected)</span>' : ''}
                        </div>
                        <div class="network-details">
                            Security: ${network.security || 'Unknown'}
                        </div>
                    </div>`;
            
            // Only show action buttons if not connected
            if (!isConnected) {
                html += `
                    <div class="network-actions">
                        <button class="action-button connect-saved-btn" data-ssid="${network.ssid}">
                            <i class="fas fa-wifi"></i> Connect
                        </button>
                        <button class="action-button danger forget-btn" data-ssid="${network.ssid}">
                            <i class="fas fa-trash-alt"></i> Forget
                        </button>
                    </div>`;
            } else {
                html += `<div class="network-actions"></div>`;
            }
            
            html += `</div>`;
        });
        
        savedList.innerHTML = html;
        
        // Add event listeners to buttons
        document.querySelectorAll('.connect-saved-btn').forEach(button => {
            button.addEventListener('click', function() {
                const ssid = this.getAttribute('data-ssid');
                connectToNetwork(ssid);
            });
        });
        
        document.querySelectorAll('.forget-btn').forEach(button => {
            button.addEventListener('click', function() {
                const ssid = this.getAttribute('data-ssid');
                forgetNetwork(ssid);
            });
        });
    }

    async function loadDiagnostics() {
        // Don't show loading indicator during refresh
        const isFirstLoad = diagnosticsResults.innerHTML.includes('loading');
        if (isFirstLoad) {
            diagnosticsResults.innerHTML = '<div class="loading">Loading...</div>';
        }
        
        const data = await fetchAPI('diagnostics');
        if (!data) return;
        
        if (!data.success) {
            diagnosticsResults.innerHTML = `<p class="text-center">${data.message}</p>`;
            return;
        }
        
        const results = data.results;
        
        diagnosticsResults.innerHTML = `
            <div class="diagnostics-grid">
                <div class="diagnostics-label">Internet Connectivity:</div>
                <div class="diagnostics-value ${results.connectivity ? 'success' : 'failure'}">
                    ${results.connectivity ? 'Connected' : 'Disconnected'}
                </div>
                
                <div class="diagnostics-label">DNS Resolution:</div>
                <div class="diagnostics-value ${results.dns_resolution ? 'success' : 'failure'}">
                    ${results.dns_resolution ? 'Working' : 'Failed'}
                </div>
                
                ${results.ping_results.avg ? `
                <div class="diagnostics-label">Ping (avg):</div>
                <div class="diagnostics-value">${results.ping_results.avg.toFixed(2)} ms</div>
                ` : ''}
            </div>
        `;
    }

    async function connectToNetwork(ssid, password = null, security = 'WPA2') {
        showToast(`Connecting to ${ssid}...`, 'warning');
        
        const data = await fetchAPI('connect', 'POST', {
            ssid,
            password,
            security
        });
        
        if (!data) return;
        
        if (data.success) {
            showToast(`Connected to ${ssid}`, 'success');
            loadCurrentConnection();
            loadSavedNetworks();
            loadDiagnostics();
        } else {
            showToast(`Failed to connect: ${data.message}`, 'error');
        }
    }

    async function forgetNetwork(ssid) {
        showToast(`Forgetting ${ssid}...`, 'warning');
        
        const data = await fetchAPI('forget', 'POST', { ssid });
        
        if (!data) return;
        
        if (data.success) {
            showToast(`Forgot network: ${ssid}`, 'success');
            loadSavedNetworks();
        } else {
            showToast(`Failed: ${data.message}`, 'error');
        }
    }

    async function runPingTest() {
        const target = pingTarget.value.trim() || '8.8.8.8';
        
        pingResults.classList.remove('hidden');
        pingOutput.textContent = 'Running ping test...';
        
        const data = await fetchAPI('ping', 'POST', { target, count: 4 });
        
        if (!data) {
            pingOutput.textContent = 'Error running ping test';
            return;
        }
        
        pingOutput.textContent = data.output;
    }

    // UI Helpers
    function showPasswordModal(ssid) {
        selectedNetwork = ssid;
        modalNetworkName.textContent = ssid;
        passwordInput.value = '';
        passwordModal.classList.remove('hidden');
    }

    function closeModal() {
        passwordModal.classList.add('hidden');
        selectedNetwork = null;
    }

    function connectWithPassword(event) {
        event.preventDefault();
        
        if (!selectedNetwork) return;
        
        const password = passwordInput.value;
        
        if (!password) {
            showToast('Please enter a password', 'error');
            return;
        }
        
        connectToNetwork(selectedNetwork, password);
        closeModal();
    }

    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        toastContainer.appendChild(toast);
        
        // Remove toast after animation completes
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    function getSignalClass(signalStrength) {
        if (!signalStrength) return 'signal-weak';
        
        const strength = parseInt(signalStrength);
        
        if (strength >= 80) return 'signal-excellent';
        if (strength >= 60) return 'signal-good';
        if (strength >= 40) return 'signal-medium';
        return 'signal-weak';
    }

    // Handle modal clicks outside content area
    window.addEventListener('click', function(event) {
        if (event.target === passwordModal) {
            closeModal();
        }
    });
});
