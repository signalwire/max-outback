/**
 * Bartender AI - Frontend JavaScript
 * Based on Holy Guacamole architecture
 */

// Configuration - SignalWire token
const STATIC_TOKEN = 'eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIiwidHlwIjoiU0FUIiwiY2giOiJwdWMuc2lnbmFsd2lyZS5jb20ifQ..iOWNWlKaEvCJFrtQ.822xSKCGWvRirCsHUZekctIy4y0CEz8JsIW3i667a1SLW2joTAnsA5hcyHMh8ySREQ-ZQxvAH95shOAHI3xblKNRo1iXITBCNFuPM0gtMgHE0k1gHrLJ7DXsjmsud5RhjxpWVOQ6Vk0AiFDVj67g92vKXYHobrHzKPfmnIY0mk2_Yb0vgvRurI155kkNnfH5Ef1hb62_7BiYCUtQ4MdiQMFS36RumncPjAiOFFKb09mofdjbyrZt8tEV_UY8QKWw15C0pF3KHdEFXUL_on7r5uo09C-NTIzPVhp-kf1cGuyjEolOLNZM21w-FljIPFSgMltuxYPjPIKRygNcxQJWWPuawFdEhxetjkavpKb1RzEuE_RXqJ_Sjo-khDlPAC5IfqknR7Hhf9CQFMSO1uOcjmDAw1xJVpvEweEFuGfWXo73IGEqk3-nuNUMfJ4YNZMBS4CYXK4gsf6FJTJEWm8Hwu2x_yhzUG8-5UUdZz5sppKe9JhlT2LfF8qSwz_jVJIksWkp8hin9lv82djDrYADv-EJpgk_8PY7YMAf7bdr.NS8yoXQtnyQDz7cmclloQA';

// DOM Elements
const connectBtn = document.getElementById('connectBtn');
const hangupBtn = document.getElementById('hangupBtn');
const muteBtn = document.getElementById('muteBtn');
const statusDiv = document.getElementById('status');
const tabItemsDiv = document.getElementById('tab-items');
const tabTotalsDiv = document.getElementById('tab-totals');
const subtotalSpan = document.getElementById('subtotal');
const taxSpan = document.getElementById('tax');
const totalSpan = document.getElementById('total');
const resultMessage = document.getElementById('result-message');
const startMutedCheckbox = document.getElementById('startMuted');
const happyHourBanner = document.getElementById('happy-hour-banner');

// SignalWire variables
let client = null;
let roomSession = null;
let isMuted = false;

// Tab state
let tabDisplay = {
    items: [],
    subtotal: 0,
    tax: 0,
    total: 0,
    tipSuggestions: null
};

// Update status display
function updateStatus(message) {
    statusDiv.textContent = message;
}

// Show temporary result message
function showResult(message, duration = 3000) {
    resultMessage.textContent = message;
    resultMessage.classList.add('show');
    setTimeout(() => {
        resultMessage.classList.remove('show');
    }, duration);
}

// Format price
function formatPrice(price) {
    return `$${price.toFixed(2)}`;
}

// Update tab display
function updateTabDisplay() {
    if (tabDisplay.items.length === 0) {
        tabItemsDiv.innerHTML = `
            <div style="text-align: center; color: #b8a878; padding: 50px;">
                Your drinks will appear here
            </div>
        `;
        tabTotalsDiv.style.display = 'none';
    } else {
        // Build items HTML
        let itemsHtml = '';
        tabDisplay.items.forEach(item => {
            const quantity = item.quantity > 1 ? `${item.quantity}x ` : '';
            const mods = item.modifications ? ` (${item.modifications})` : '';
            itemsHtml += `
                <div class="tab-item">
                    <div>
                        <div class="tab-item-name">${quantity}${item.name}${mods}</div>
                        <div class="tab-item-desc">${item.description || ''}</div>
                    </div>
                    <div class="tab-item-price">${formatPrice(item.total)}</div>
                </div>
            `;
        });
        
        tabItemsDiv.innerHTML = itemsHtml;
        
        // Update totals
        subtotalSpan.textContent = formatPrice(tabDisplay.subtotal);
        taxSpan.textContent = formatPrice(tabDisplay.tax);
        
        // Show tip suggestions if available
        if (tabDisplay.tipSuggestions) {
            let tipHtml = `
                <div class="tip-options" style="margin: 15px 0; padding: 10px; background: rgba(212, 175, 55, 0.2); border-radius: 8px;">
                    <div style="font-weight: bold; margin-bottom: 10px; color: #d4af37;">Tip Options:</div>
            `;
            
            Object.entries(tabDisplay.tipSuggestions).forEach(([percent, data]) => {
                tipHtml += `
                    <div class="tip-option" style="padding: 5px 10px; margin: 5px 0; background: rgba(0,0,0,0.5); border-radius: 4px; display: flex; justify-content: space-between;">
                        <span>${percent}% tip (${formatPrice(data.amount)}):</span>
                        <span style="font-weight: bold; color: #d4af37;">${formatPrice(data.total)}</span>
                    </div>
                `;
            });
            
            tipHtml += '</div>';
            
            // Insert tip options before the total
            const totalLine = document.querySelector('.total-line.final');
            if (totalLine) {
                const tipContainer = document.getElementById('tip-container');
                if (tipContainer) {
                    tipContainer.innerHTML = tipHtml;
                } else {
                    const newTipContainer = document.createElement('div');
                    newTipContainer.id = 'tip-container';
                    newTipContainer.innerHTML = tipHtml;
                    totalLine.parentNode.insertBefore(newTipContainer, totalLine);
                }
            }
            
            totalSpan.textContent = formatPrice(tabDisplay.total) + ' (before tip)';
        } else {
            // Remove tip container if it exists
            const tipContainer = document.getElementById('tip-container');
            if (tipContainer) {
                tipContainer.remove();
            }
            totalSpan.textContent = formatPrice(tabDisplay.total);
        }
        
        tabTotalsDiv.style.display = 'block';
    }
}

// Handle user events from the agent
function handleUserEvent(params) {
    console.log('User event:', params);
    
    // Extract event data - handle different event structures
    let eventData = params;
    if (params && params.params) {
        eventData = params.params;
    }
    if (params && params.event) {
        eventData = params.event;
    }
    
    // Validate event data
    if (!eventData || !eventData.type) {
        console.log('No valid event data found');
        return;
    }
    
    switch(eventData.type) {
        case 'drink_added':
            // Update tab with new drink
            const existingItem = tabDisplay.items.find(i => 
                i.sku === eventData.drink.sku && 
                i.modifications === eventData.drink.modifications
            );
            
            if (existingItem) {
                existingItem.quantity = eventData.drink.quantity;
                existingItem.total = eventData.drink.total;
            } else {
                tabDisplay.items.push(eventData.drink);
            }
            
            tabDisplay.subtotal = eventData.subtotal;
            tabDisplay.tax = eventData.tax;
            tabDisplay.total = eventData.total;
            
            updateTabDisplay();
            updateStatus(`Added ${eventData.drink.name} to your tab`);
            showResult(`+${eventData.drink.name}`, 2000);
            break;
            
        case 'drink_removed':
            // Update tab from backend after removal
            if (eventData.items) {
                tabDisplay.items = eventData.items;
            }
            tabDisplay.subtotal = eventData.subtotal || 0;
            tabDisplay.tax = eventData.tax || 0;
            tabDisplay.total = eventData.total || 0;
            updateTabDisplay();
            updateStatus(`Removed ${eventData.drink_name} from your tab`);
            showResult(`-${eventData.drink_name}`, 2000);
            break;
            
        case 'tab_review':
            // Sync tab from backend
            if (eventData.items) {
                tabDisplay.items = eventData.items;
                tabDisplay.subtotal = eventData.subtotal;
                tabDisplay.tax = eventData.tax;
                tabDisplay.total = eventData.total;
                tabDisplay.tipSuggestions = eventData.tip_suggestions || null;
                updateTabDisplay();
            }
            if (eventData.tip_suggestions) {
                updateStatus('Choose your tip amount');
            } else {
                updateStatus('Here\'s your current tab');
            }
            break;
            
        case 'tab_closed':
            // Clear tab after payment
            tabDisplay.items = [];
            tabDisplay.subtotal = 0;
            tabDisplay.tax = 0;
            tabDisplay.total = 0;
            tabDisplay.tipSuggestions = null;
            updateTabDisplay();
            updateStatus('Tab closed. Thank you!');
            showResult(`Total paid: ${formatPrice(eventData.final_total)}`, 5000);
            break;
            
        case 'happy_hour_status':
            // Update happy hour banner
            if (eventData.active) {
                happyHourBanner.classList.add('active');
            } else {
                happyHourBanner.classList.remove('active');
            }
            updateStatus(eventData.message);
            break;
            
    }
}

// Connect to SignalWire
async function connect() {
    try {
        connectBtn.disabled = true;
        connectBtn.textContent = 'Connecting...';
        updateStatus('Connecting to bartender...');
        
        // Check token
        if (!STATIC_TOKEN || STATIC_TOKEN === 'YOUR_TOKEN_HERE') {
            throw new Error('Please update STATIC_TOKEN with your actual SignalWire token');
        }
        
        // Initialize SignalWire client
        if (window.SignalWire && typeof window.SignalWire.SignalWire === 'function') {
            console.log('Initializing SignalWire client...');
            client = await window.SignalWire.SignalWire({
                token: STATIC_TOKEN,
                logLevel: 'debug'
            });
        } else {
            throw new Error('SignalWire SDK not loaded');
        }
        
        console.log('Client initialized');
        
        // Subscribe to client events (some events come through client, not just room)
        client.on('user_event', (params) => {
            console.log('User event from client:', params);
            handleUserEvent(params);
        });
        
        // Get video container
        const videoContainer = document.getElementById('video-container');
        
        // Dial the bartender agent
        console.log('Dialing bartender agent...');
        roomSession = await client.dial({
            to: '/public/bartender',
            rootElement: videoContainer,
            audio: true,
            video: true,
            negotiateVideo: true  // Important for video negotiation
        });
        
        console.log('Room session created:', roomSession);
        
        // Set up room event listeners
        roomSession.on('member.talking.started', (event) => {
            console.log('Member talking started:', event);
        });
        
        roomSession.on('member.talking.ended', (event) => {
            console.log('Member talking ended:', event);
        });
        
        roomSession.on('room.ended', () => {
            console.log('Room ended');
            disconnect();
        });
        
        // Listen for user events from room session
        roomSession.on('user_event', (params) => {
            console.log('User event from room:', params);
            handleUserEvent(params);
        });
        
        // Start the call
        await roomSession.start();
        
        // Hide the video placeholder once video starts
        const placeholder = document.getElementById('video-placeholder');
        if (placeholder) {
            placeholder.style.display = 'none';
        }
        
        // Handle initial mute state
        if (startMutedCheckbox.checked) {
            toggleMute();
        }
        
        // Update UI
        connectBtn.style.display = 'none';
        hangupBtn.style.display = 'inline-block';
        muteBtn.style.display = 'inline-block';
        muteBtn.textContent = isMuted ? '🔊 Unmute' : '🔇 Mute';
        
        updateStatus('Connected! What can I get you?');
        
    } catch (error) {
        console.error('Connection error:', error);
        updateStatus('Connection failed. Please check your token and try again.');
        connectBtn.disabled = false;
        connectBtn.textContent = '🎤 Start Ordering';
    }
}

// Disconnect
function disconnect() {
    // Try to hangup the room session if it exists and is connected
    if (roomSession) {
        try {
            // Only try to hangup if the session is still active
            if (roomSession.active !== false) {
                roomSession.hangup();
            }
        } catch (error) {
            console.log('Session already ended:', error);
        }
        roomSession = null;
    }
    
    // Disconnect the client if it exists
    if (client) {
        try {
            client.disconnect();
        } catch (error) {
            console.log('Client disconnect error:', error);
        }
        client = null;
    }
    
    // Reset UI
    connectBtn.style.display = 'inline-block';
    connectBtn.disabled = false;
    connectBtn.textContent = '🎤 Start Ordering';
    hangupBtn.style.display = 'none';
    muteBtn.style.display = 'none';
    
    // Clear and restore placeholder
    const videoContainer = document.getElementById('video-container');
    videoContainer.innerHTML = '';
    const placeholder = document.createElement('div');
    placeholder.id = 'video-placeholder';
    placeholder.innerHTML = `
        <img src="/logo.png" alt="Outback Bar Logo">
        <p>Welcome to Outback Bar</p>
        <p>Click "Start Ordering" to talk with Max</p>
    `;
    videoContainer.appendChild(placeholder);
    
    updateStatus('Disconnected. Thanks for visiting Outback Bar!');
}

// Toggle mute
function toggleMute() {
    if (!roomSession) return;
    
    if (isMuted) {
        roomSession.audioUnmute();
        muteBtn.textContent = '🔇 Mute';
        isMuted = false;
    } else {
        roomSession.audioMute();
        muteBtn.textContent = '🔊 Unmute';
        isMuted = true;
    }
}

// Hangup
async function hangup() {
    updateStatus('Ending call...');
    
    try {
        if (roomSession && roomSession.active !== false) {
            await roomSession.hangup();
        }
    } catch (error) {
        console.error('Hangup error:', error);
    }
    
    // Clean up everything
    roomSession = null;
    
    if (client) {
        try {
            client.disconnect();
        } catch (error) {
            console.log('Client disconnect error:', error);
        }
        client = null;
    }
    
    // Reset UI
    connectBtn.style.display = 'inline-block';
    connectBtn.disabled = false;
    connectBtn.textContent = '🎤 Start Ordering';
    hangupBtn.style.display = 'none';
    muteBtn.style.display = 'none';
    
    // Clear and restore placeholder
    const videoContainer = document.getElementById('video-container');
    videoContainer.innerHTML = '';
    const placeholder = document.createElement('div');
    placeholder.id = 'video-placeholder';
    placeholder.innerHTML = `
        <img src="/logo.png" alt="Outback Bar Logo">
        <p>Welcome to Outback Bar</p>
        <p>Click "Start Ordering" to talk with Max</p>
    `;
    videoContainer.appendChild(placeholder);
    
    updateStatus('Disconnected. Thanks for visiting Outback Bar!');
}

// Load menu from backend
async function loadMenu() {
    try {
        const response = await fetch('/api/menu');
        const data = await response.json();
        const menu = data.menu;
        
        let menuHtml = '';
        
        // Process each category
        Object.entries(menu).forEach(([category, items]) => {
            menuHtml += `<div class="menu-category">`;
            menuHtml += `<div class="menu-category-title">${category.replace('_', ' ')}</div>`;
            
            Object.entries(items).forEach(([sku, item]) => {
                const abv = item.abv > 0 ? `<span class="abv-indicator">${item.abv}%</span>` : '';
                menuHtml += `
                    <div class="menu-item">
                        <div class="menu-item-info">
                            <div class="menu-item-name">${item.name}${abv}</div>
                            <div class="menu-item-desc">${item.description}</div>
                        </div>
                        <div class="menu-item-price">${formatPrice(item.price)}</div>
                    </div>
                `;
            });
            
            menuHtml += `</div>`;
        });
        
        document.getElementById('menu-display').innerHTML = menuHtml;
        
    } catch (error) {
        console.error('Failed to load menu:', error);
    }
}

// Check happy hour status
async function checkHappyHour() {
    try {
        const response = await fetch('/api/happy-hour');
        const data = await response.json();
        
        if (data.active) {
            happyHourBanner.classList.add('active');
        } else {
            happyHourBanner.classList.remove('active');
        }
    } catch (error) {
        console.error('Failed to check happy hour:', error);
    }
}

// Event listeners
connectBtn.addEventListener('click', connect);
hangupBtn.addEventListener('click', hangup);
muteBtn.addEventListener('click', toggleMute);

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    loadMenu();
    checkHappyHour();
    updateTabDisplay();
    updateStatus('Welcome to Outback Bar! What can I get you?');
    
    // Check happy hour every minute
    setInterval(checkHappyHour, 60000);
});