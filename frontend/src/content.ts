import axios from 'axios';

console.log('Content script loaded');

// Example: Send a message to the background script
chrome.runtime.sendMessage({ type: 'contentScriptLoaded' }, (response) => {
  console.log('Response from background:', response);
});

// Check if we're on Gmail
if (window.location.hostname === 'mail.google.com') {
  // Create and inject the chatbox container
  const chatboxContainer = document.createElement('div');
  chatboxContainer.id = 'email-bot-chatbox';
  chatboxContainer.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 350px;
    height: 300px;
    background: linear-gradient(145deg, #0a1929, #0d2b3e);
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2),
                0 0 0 1px rgba(64, 224, 208, 0.1);
    display: flex;
    flex-direction: column;
    z-index: 9999;
    font-family: 'Google Sans', Arial, sans-serif;
    transition: height 0.3s ease;
    overflow: hidden;
  `;

  // Create chatbox header
  const header = document.createElement('div');
  header.id = 'chatbox-header';
  header.style.cssText = `
    padding: 12px 16px;
    background: linear-gradient(145deg, #0d2b3e, #0a1929);
    color: #ffffff;
    border-radius: 16px 16px 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: move;
    user-select: none;
    border-bottom: 1px solid rgba(64, 224, 208, 0.1);
  `;
  header.innerHTML = `
    <div style="display: flex; align-items: center; gap: 8px;">
      <div style="width: 8px; height: 8px; background: #40e0d0; border-radius: 50%; box-shadow: 0 0 12px #40e0d0;"></div>
      <span style="font-weight: 500;">AI Email Assistant</span>
    </div>
    <div style="display: flex; gap: 8px;">
      <button id="settings-button" style="background: none; border: none; color: #ffffff; cursor: pointer; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border-radius: 4px; transition: background 0.2s;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" fill="currentColor"/>
        </svg>
      </button>
      <button id="minimize-chat" style="background: none; border: none; color: #ffffff; cursor: pointer; font-size: 18px; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border-radius: 4px; transition: background 0.2s;">−</button>
    </div>
  `;

  // Create messages container
  const messagesContainer = document.createElement('div');
  messagesContainer.id = 'chat-messages';
  messagesContainer.style.cssText = `
    flex: 1;
    padding: 16px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
    background: linear-gradient(145deg, #0a1929, #0d2b3e);
    scrollbar-width: thin;
    scrollbar-color: rgba(64, 224, 208, 0.2) transparent;
  `;

  // Add scrollbar styles
  const scrollbarStyle = document.createElement('style');
  scrollbarStyle.textContent = `
    #chat-messages::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    
    #chat-messages::-webkit-scrollbar-track {
      background: transparent;
    }
    
    #chat-messages::-webkit-scrollbar-thumb {
      background-color: rgba(64, 224, 208, 0.2);
      border-radius: 3px;
      transition: all 0.2s;
    }
    
    #chat-messages::-webkit-scrollbar-thumb:hover {
      background-color: rgba(64, 224, 208, 0.3);
    }
    
    #chat-messages::-webkit-scrollbar-corner {
      background: transparent;
    }
  `;
  document.head.appendChild(scrollbarStyle);

  // Assemble the chatbox
  chatboxContainer.appendChild(header);
  chatboxContainer.appendChild(messagesContainer);
  document.body.appendChild(chatboxContainer);

  // Draggable functionality
  let isDragging = false;
  let currentX: number;
  let currentY: number;
  let initialX: number;
  let initialY: number;
  let xOffset = 0;
  let yOffset = 0;

  chatboxContainer.addEventListener('mousedown', dragStart);
  document.addEventListener('mousemove', drag);
  document.addEventListener('mouseup', dragEnd);

  function dragStart(e: MouseEvent) {
    // Don't start drag if clicking on input or buttons
    const target = e.target as HTMLElement;
    if (target instanceof HTMLInputElement || 
        target instanceof HTMLButtonElement ||
        target.closest('button')) {
      return;
    }

    initialX = e.clientX - xOffset;
    initialY = e.clientY - yOffset;
    isDragging = true;
  }

  function drag(e: MouseEvent) {
    if (isDragging) {
      e.preventDefault();
      currentX = e.clientX - initialX;
      currentY = e.clientY - initialY;

      xOffset = currentX;
      yOffset = currentY;

      chatboxContainer.style.transform = `translate3d(${currentX}px, ${currentY}px, 0)`;
    }
  }

  function dragEnd() {
    isDragging = false;
  }

  // Minimize functionality
  const minimizeButton = document.getElementById('minimize-chat');
  if (minimizeButton) {
    minimizeButton.addEventListener('click', () => {
      const isMinimized = chatboxContainer.style.height === '60px';
      chatboxContainer.style.height = isMinimized ? '300px' : '60px';
      
      if (isMinimized) {
        // Expanding
        messagesContainer.style.display = 'flex';
        chatboxContainer.style.background = 'linear-gradient(145deg, #0a1929, #0d2b3e)';
      } else {
        // Collapsing
        messagesContainer.style.display = 'none';
        chatboxContainer.style.background = 'linear-gradient(145deg, #0a1929, #0d2b3e)';
      }
      
      minimizeButton.textContent = isMinimized ? '−' : '+';
    });
  }

  // Create settings overlay
  const settingsOverlay = document.createElement('div');
  settingsOverlay.id = 'settings-overlay';
  settingsOverlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(8px);
    display: none;
    justify-content: center;
    align-items: center;
    z-index: 10000;
  `;

  const settingsContainer = document.createElement('div');
  settingsContainer.style.cssText = `
    background: linear-gradient(145deg, #0d2b3e, #0a1929);
    border-radius: 16px;
    padding: 24px;
    width: 90%;
    max-width: 800px;
    max-height: 90vh;
    overflow-y: auto;
    position: relative;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3),
                0 0 0 1px rgba(64, 224, 208, 0.1);
  `;

  // Add close button
  const closeButton = document.createElement('button');
  closeButton.innerHTML = `
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" fill="#ffffff"/>
    </svg>
  `;
  closeButton.style.cssText = `
    position: absolute;
    top: 16px;
    right: 16px;
    background: rgba(64, 224, 208, 0.1);
    border: none;
    color: #ffffff;
    cursor: pointer;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: all 0.2s;
  `;
  closeButton.addEventListener('mouseover', () => {
    closeButton.style.background = 'rgba(64, 224, 208, 0.2)';
    closeButton.style.boxShadow = '0 0 12px rgba(64, 224, 208, 0.1)';
  });
  closeButton.addEventListener('mouseout', () => {
    closeButton.style.background = 'rgba(64, 224, 208, 0.1)';
    closeButton.style.boxShadow = 'none';
  });

  // Add settings content
  settingsContainer.innerHTML = `
    <h1 style="margin: 0 0 24px 0; display: flex; align-items: center; gap: 8px; color: #ffffff;">
      <span style="width: 8px; height: 8px; background: #40e0d0; border-radius: 50%; box-shadow: 0 0 12px #40e0d0;"></span>
      Email Bot Settings
    </h1>
    
    <div style="margin-bottom: 32px;">
      <h2 style="color: #40e0d0; margin: 0 0 16px 0; font-size: 18px;">Email Management</h2>
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px; background: rgba(10, 25, 41, 0.5); border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(64, 224, 208, 0.1);">
        <div style="flex: 1;">
          <div style="font-weight: 500; margin-bottom: 4px; color: #ffffff;">Auto Send Emails</div>
          <div style="color: #a0a0a0; font-size: 14px;">Automatically send emails without confirmation</div>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" id="auto-send-toggle">
          <span class="toggle-slider"></span>
        </label>
      </div>
      
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px; background: rgba(10, 25, 41, 0.5); border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(64, 224, 208, 0.1);">
        <div style="flex: 1;">
          <div style="font-weight: 500; margin-bottom: 4px; color: #ffffff;">Auto Spam Recovery</div>
          <div style="color: #a0a0a0; font-size: 14px;">Automatically rescue legitimate emails from spam folder</div>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" id="auto-spam-recovery-toggle">
          <span class="toggle-slider"></span>
        </label>
      </div>
    </div>

    <div style="margin-bottom: 32px;">
      <h2 style="color: #40e0d0; margin: 0 0 16px 0; font-size: 18px;">Automation</h2>
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px; background: rgba(10, 25, 41, 0.5); border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(64, 224, 208, 0.1);">
        <div style="flex: 1;">
          <div style="font-weight: 500; margin-bottom: 4px; color: #ffffff;">Headless Mode</div>
          <div style="color: #a0a0a0; font-size: 14px;">Run automated tasks invisibly in the background</div>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" id="headless-selenium-toggle">
          <span class="toggle-slider"></span>
        </label>
      </div>
      
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px; background: rgba(10, 25, 41, 0.5); border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(64, 224, 208, 0.1);">
        <div style="flex: 1;">
          <div style="font-weight: 500; margin-bottom: 4px; color: #ffffff;">Phone Number</div>
          <div style="color: #a0a0a0; font-size: 14px;">Number for SMS notifications</div>
        </div>
        <input 
          type="text" 
          id="phone-number-input" 
          placeholder="Enter phone number" 
          style="
            background: rgba(10, 25, 41, 0.5); 
            border: 1px solid rgba(64, 224, 208, 0.3); 
            color: white; 
            padding: 8px; 
            border-radius: 4px;
            width: 200px;
          "
        >
      </div>
    </div>

    <div id="settings-status" style="color: #40e0d0; text-align: center; margin-top: 20px; min-height: 24px;"></div>
    <div style="display: flex; justify-content: center; margin-top: 16px;">
      <button 
        id="save-settings-button" 
        style="
          background: rgba(64, 224, 208, 0.2); 
          border: 1px solid rgba(64, 224, 208, 0.4); 
          color: #40e0d0; 
          padding: 10px 20px; 
          border-radius: 4px; 
          cursor: pointer; 
          font-weight: bold;
          transition: all 0.2s;
        "
      >Save Settings</button>
    </div>
  `;

  // Add toggle switch styles
  const style = document.createElement('style');
  style.textContent = `
    .toggle-switch {
      position: relative;
      display: inline-block;
      width: 50px;
      height: 24px;
      margin-left: 16px;
    }
    .toggle-switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }
    .toggle-slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: rgba(64, 224, 208, 0.1);
      transition: .4s;
      border-radius: 24px;
      box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    .toggle-slider:before {
      position: absolute;
      content: "";
      height: 20px;
      width: 20px;
      left: 2px;
      bottom: 2px;
      background-color: white;
      transition: .4s;
      border-radius: 50%;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    input:checked + .toggle-slider {
      background-color: rgba(64, 224, 208, 0.3);
    }
    input:checked + .toggle-slider:before {
      transform: translateX(26px);
      background-color: #40e0d0;
      background-color: #00ff9d;
      box-shadow: 0 0 8px rgba(0, 255, 157, 0.5);
    }
  `;
  document.head.appendChild(style);

  settingsContainer.appendChild(closeButton);
  settingsOverlay.appendChild(settingsContainer);
  document.body.appendChild(settingsOverlay);

  // Get references to settings controls
  const headlessSeleniumToggle = document.getElementById('headless-selenium-toggle') as HTMLInputElement;
  const autoSendToggle = document.getElementById('auto-send-toggle') as HTMLInputElement;
  const autoSpamRecoveryToggle = document.getElementById('auto-spam-recovery-toggle') as HTMLInputElement;
  const phoneNumberInput = document.getElementById('phone-number-input') as HTMLInputElement;
  const saveSettingsButton = document.getElementById('save-settings-button') as HTMLButtonElement;
  const settingsStatus = document.getElementById('settings-status') as HTMLDivElement;

  // Function to get user settings from backend
  async function fetchSettings() {
    try {
      settingsStatus.textContent = 'Fetching settings...';
      settingsStatus.style.color = '#40e0d0';

      // First get the user's email from the /email endpoint
      const emailResponse = await fetch('http://localhost:8000/email');
      const emailData = await emailResponse.json();
      
      if (!emailData.email) {
        settingsStatus.textContent = 'Error: Could not retrieve email address';
        settingsStatus.style.color = '#ff5555';
        return;
      }

      const userEmail = emailData.email;
      
      // Use the email as a query parameter
      const response = await fetch(`http://localhost:8000/settings?email=${encodeURIComponent(userEmail)}`);

      if (response.ok) {
        const data = await response.json();
        console.log('Fetched settings:', data);
        
        // Update UI with fetched settings
        if (data.settings) {
          headlessSeleniumToggle.checked = data.settings.headless_selenium || false;
          autoSendToggle.checked = data.settings.auto_send || false;
          autoSpamRecoveryToggle.checked = data.settings.auto_spam_recovery || false;
          phoneNumberInput.value = data.settings.phone_number || '';
        }
        
        settingsStatus.textContent = '';
      } else {
        const errorData = await response.json();
        settingsStatus.textContent = `Error: ${errorData.detail || 'Failed to load settings'}`;
        settingsStatus.style.color = '#ff5555';
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
      settingsStatus.textContent = 'Error connecting to server';
      settingsStatus.style.color = '#ff5555';
    }
  }

  // Function to save settings to backend
  async function saveSettings() {
    try {
      settingsStatus.textContent = 'Saving settings...';
      settingsStatus.style.color = '#40e0d0';

      // First get the user's email from the /email endpoint
      const emailResponse = await fetch('http://localhost:8000/email');
      const emailData = await emailResponse.json();
      
      if (!emailData.email) {
        settingsStatus.textContent = 'Error: Could not retrieve email address';
        settingsStatus.style.color = '#ff5555';
        return;
      }

      const userEmail = emailData.email;

      // Collect settings from UI
      const settings = {
        headless_selenium: headlessSeleniumToggle.checked,
        auto_send: autoSendToggle.checked,
        auto_spam_recovery: autoSpamRecoveryToggle.checked,
        phone_number: phoneNumberInput.value || null,
        email: userEmail // Include email in the settings payload
      };

      // Send settings to backend
      const response = await fetch('http://localhost:8000/settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
      });

      if (response.ok) {
        settingsStatus.textContent = 'Settings saved successfully!';
        setTimeout(() => {
          settingsStatus.textContent = '';
        }, 3000);
      } else {
        const errorData = await response.json();
        settingsStatus.textContent = `Error: ${errorData.detail || 'Failed to save settings'}`;
        settingsStatus.style.color = '#ff5555';
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      settingsStatus.textContent = 'Error connecting to server';
      settingsStatus.style.color = '#ff5555';
    }
  }

  // Add event listeners
  saveSettingsButton.addEventListener('click', saveSettings);

  // Update settings button functionality
  const settingsButton = document.getElementById('settings-button');
  if (settingsButton) {
    settingsButton.addEventListener('click', () => {
      settingsOverlay.style.display = 'flex';
      // Fetch current settings when opening settings panel
      fetchSettings();
    });
  }

  closeButton.addEventListener('click', () => {
    settingsOverlay.style.display = 'none';
  });

  // Close settings when clicking outside
  settingsOverlay.addEventListener('click', (e) => {
    if (e.target === settingsOverlay) {
      settingsOverlay.style.display = 'none';
    }
  });

  // Create quick actions panel
  const quickActionsPanel = document.createElement('div');
  quickActionsPanel.id = 'quick-actions-panel';
  quickActionsPanel.style.cssText = `
    position: fixed;
    bottom: 20px;
    left: 20px;
    background: linear-gradient(145deg, #0a1929, #0d2b3e);
    border-radius: 16px;
    padding: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2),
                0 0 0 1px rgba(64, 224, 208, 0.1);
    display: flex;
    flex-direction: column;
    gap: 8px;
    z-index: 9999;
  `;

  const retrainButton = document.createElement('button');
  retrainButton.innerHTML = `
    <div style="display: flex; align-items: center; gap: 8px;">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z" fill="#40e0d0"/>
      </svg>
      <span>Retrain</span>
    </div>
  `;
  retrainButton.style.cssText = `
    padding: 8px 16px;
    background: rgba(64, 224, 208, 0.1);
    color: #ffffff;
    border: 1px solid rgba(64, 224, 208, 0.2);
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    font-size: 14px;
    font-weight: 500;
  `;

  retrainButton.addEventListener('mouseover', () => {
    retrainButton.style.background = 'rgba(64, 224, 208, 0.2)';
    retrainButton.style.borderColor = 'rgba(64, 224, 208, 0.3)';
    retrainButton.style.boxShadow = '0 0 12px rgba(64, 224, 208, 0.2)';
  });

  retrainButton.addEventListener('mouseout', () => {
    retrainButton.style.background = 'rgba(64, 224, 208, 0.1)';
    retrainButton.style.borderColor = 'rgba(64, 224, 208, 0.2)';
    retrainButton.style.boxShadow = 'none';
  });

  async function fetchReTrain() {
    let loadingMessage = addMessage('Training Persona.', 'bot');
    let dots = 1;
    const loadingInterval = setInterval(() => {
      dots = (dots % 3) + 1;
      loadingMessage.textContent = 'Training Persona' + '.'.repeat(dots);
    }, 500);

    try {
      const response = await axios.get('http://127.0.0.1:8000/index');
      console.log('Data fetched:', response.data);
      clearInterval(loadingInterval);
      addMessage('Persona Trained Successfully!', 'bot', '', response.data.PersonaSummary);
    } catch (error) {
      console.error('Error fetching data:', error);
      clearInterval(loadingInterval);
      addMessage('Error training persona. Please try again.', 'bot');
    }
  }

  retrainButton.addEventListener('click', () => {
    addAIAction("Retrained model to update your AI persona", new Date());
    fetchReTrain();
  });

  const smartSortButton = document.createElement('button');
  smartSortButton.innerHTML = `
    <div style="display: flex; align-items: center; gap: 8px;">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 18h6v-2H3v2zM3 6v2h18V6H3zm0 7h12v-2H3v2z" fill="#40e0d0"/>
      </svg>
      <span>Smart Sort</span>
    </div>
  `;
  smartSortButton.style.cssText = `
    padding: 8px 16px;
    background: rgba(64, 224, 208, 0.1);
    color: #ffffff;
    border: 1px solid rgba(64, 224, 208, 0.2);
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    font-size: 14px;
    font-weight: 500;
  `;

  smartSortButton.addEventListener('mouseover', () => {
    smartSortButton.style.background = 'rgba(64, 224, 208, 0.2)';
    smartSortButton.style.borderColor = 'rgba(64, 224, 208, 0.3)';
    smartSortButton.style.boxShadow = '0 0 12px rgba(64, 224, 208, 0.2)';
  });

  smartSortButton.addEventListener('mouseout', () => {
    smartSortButton.style.background = 'rgba(64, 224, 208, 0.1)';
    smartSortButton.style.borderColor = 'rgba(64, 224, 208, 0.2)';
    smartSortButton.style.boxShadow = 'none';
  });

  smartSortButton.addEventListener('click', async () => {
    try {
      addMessage('Starting smart sort automation...', 'bot', 'color: #40e0d0;');
      addAIAction("Smart sorted unread emails into appropriate categories", new Date());
      
      const response = await fetch('http://localhost:8000/gmail/automate');
      const result = await response.json();
      
      if (result.status === 'success') {
        addMessage('Smart sort completed successfully!', 'bot', 'color: #00ff9d;');
        if (result.refresh) {
          // Wait a moment to show the success message before refreshing
          setTimeout(() => {
            window.location.reload();
          }, 1000);
        }
      } else {
        addMessage(`Error during smart sort: ${result.detail}`, 'bot', 'color: #ff4444;');
      }
    } catch (error) {
      addMessage(`Failed to run smart sort: ${error}`, 'bot', 'color: #ff4444;');
    }
  });

  quickActionsPanel.appendChild(retrainButton);
  quickActionsPanel.appendChild(smartSortButton);
  document.body.appendChild(quickActionsPanel);

  // --- AI Actions Panel Logic ---

  let aiActionsPanelElement: HTMLElement | null = null; // Keep track if the panel exists globally

  // Function to create and insert the AI Actions Panel
  async function createAndInsertAIActionsPanel() {
    if (document.getElementById('ai-actions-panel')) {
        aiActionsPanelElement = document.getElementById('ai-actions-panel'); // Update reference if it somehow exists
        return; // Panel already exists
    }

    // Use a local const for the element creation
    const aiActionsPanel = document.createElement('div');
    aiActionsPanel.id = 'ai-actions-panel';
    aiActionsPanel.style.cssText = `
      position: sticky;
      top: 0; /* Stick to the top of its container */
      z-index: 9998; /* Ensure it\'s above scrolling content but below chatbox/overlay */
      background: linear-gradient(145deg, #0a1929, #0d2b3e);
      border: 1px solid rgba(64, 224, 208, 0.1);
      padding: 8px 16px;
      display: flex; /* Start visible */
      flex-direction: column;
      gap: 8px;
      max-height: 200px;
      overflow-y: auto;
      width: calc(100% - 32px); /* Adjust width slightly */
      margin: 0px 16px 8px 16px; /* Add margin */
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      transition: all 0.3s ease;
      overflow: hidden; /* Hide overflow to enforce border radius */
    `;

    // Create header for AI actions panel
    const aiActionsHeader = document.createElement('div');
    aiActionsHeader.style.cssText = `
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 4px 0;
      color: #ffffff;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
    `;
    aiActionsHeader.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px;">
        <div style="width: 6px; height: 6px; background: #40e0d0; border-radius: 50%; box-shadow: 0 0 8px #40e0d0;"></div>
        <span>AI Actions</span>
      </div>
      <button id="toggle-ai-actions" style="background: none; border: none; color: #ffffff; cursor: pointer; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border-radius: 4px; transition: all 0.2s;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M7 10l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    `;

    // Create actions container
    const actionsContainer = document.createElement('div');
    actionsContainer.id = 'ai-actions-container';
    actionsContainer.style.cssText = `
      display: flex;
      flex-direction: row;
      gap: 8px;
      overflow-x: auto;
      padding: 4px 0;
      width: 100%;
      transition: all 0.3s ease;
      opacity: 1;
      max-height: 200px;
    `;

    // Assemble the AI actions panel
    aiActionsPanel.appendChild(aiActionsHeader);
    aiActionsPanel.appendChild(actionsContainer);

    // Find the AO div's parent and insert the panel
    const aoDiv = document.querySelector('div.AO');
    if (aoDiv && aoDiv.parentNode) {
      // Insert as the first child of aoDiv's parent
      aoDiv.parentNode.insertBefore(aiActionsPanel, aoDiv.parentNode.firstChild);
      setupToggleFunctionality(aiActionsPanel, actionsContainer); // Pass the created elements
      aiActionsPanelElement = aiActionsPanel; // Assign to global tracker upon successful insertion
    } else {
      console.error('Could not find AO div or its parent for AI actions panel placement');
      aiActionsPanelElement = null; // Ensure tracker is null if insertion failed
      return;
    }

    const response = await fetch('http://localhost:8000/get-actions', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    const result = await response.json();
    console.log(result);
    result.actions.forEach((action: { action: string; created_at: string; }) => {
      addAIAction(action.action, new Date(action.created_at));
    });
  }

  // Function to setup toggle functionality
  function setupToggleFunctionality(panel: HTMLElement, container: HTMLElement) {
      const toggleButton = panel.querySelector<HTMLButtonElement>('#toggle-ai-actions');
      // Use a more specific selector for the header div containing the button
      const header = panel.querySelector<HTMLElement>('div[style*="justify-content: space-between"]');

      if (toggleButton && header) {
          toggleButton.addEventListener('click', (e) => {
              e.stopPropagation(); // Prevent event bubbling to header click listener
              const isCollapsed = container.style.maxHeight === '0px';

              if (isCollapsed) {
                  // Expand
                  container.style.maxHeight = '200px'; // Set max-height for animation
                  container.style.opacity = '1';
                  container.style.padding = '4px 0'; // Restore padding
                  toggleButton.innerHTML = `
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M7 10l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                      </svg>
                  `; // Down arrow
              } else {
                  // Collapse
                  container.style.maxHeight = '0px'; // Collapse
                  container.style.opacity = '0';
                  container.style.padding = '0'; // Remove padding when collapsed
                  toggleButton.innerHTML = `
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M7 14l5-5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                      </svg>
                  `; // Up arrow
              }
          });

          // Add click handler to header for toggling, ensuring button click doesn't trigger it
          header.addEventListener('click', (e) => {
               // Ensure the click target is the header itself or its direct children, not the button
               if (e.target === header || (e.target instanceof HTMLElement && e.target.parentElement === header && e.target.tagName !== 'BUTTON')) {
                   toggleButton.click();
               }
          });
      } else {
           console.error("Could not find toggle button or header for AI Actions Panel.");
      }
  }

  // Function to add a new action
  function addAIAction(action: string, timestamp: Date) {
    // Use the global tracker or get element by ID
    const panel = aiActionsPanelElement ?? document.getElementById('ai-actions-panel');
    if (!panel) {
        console.warn("AI Actions Panel element not found when trying to add action.");
        return;
    }
    const actionsContainer = panel.querySelector<HTMLElement>('#ai-actions-container');

    if (!actionsContainer) {
        console.error("AI Actions container not found within the panel.");
        return;
    }

    const actionElement = document.createElement('div');
    actionElement.style.cssText = `
      min-width: 180px;
      max-width: 180px;
      padding: 8px 12px;
      background: rgba(64, 224, 208, 0.1);
      border: 1px solid rgba(64, 224, 208, 0.2);
      border-radius: 8px;
      color: #ffffff;
      font-size: 13px;
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex-shrink: 0;
    `;

    const timeString = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); // Format time H:MM AM/PM
    actionElement.innerHTML = `
      <div style="color: #40e0d0; font-size: 12px;">${timeString}</div>
      <div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${action}">${action}</div>
    `;

    // Insert new action at the beginning
    actionsContainer.insertBefore(actionElement, actionsContainer.firstChild);

    // Limit to 5 actions by removing the last child if count exceeds 5
    while (actionsContainer.children.length > 5) {
        if (actionsContainer.lastChild) { // Check if lastChild exists before removing
            actionsContainer.removeChild(actionsContainer.lastChild);
        } else {
            break; // Should not happen, but break loop if lastChild is somehow null
        }
    }
  }

  // Function to check URL and update AI Actions Panel visibility
  function updateAIActionsVisibility() {
      const currentHash = window.location.hash;
      // Simple check: Show if hash is #inbox or empty/root, hide otherwise (specifically if it contains '/')
      const isOnInbox = currentHash === '#inbox' || currentHash === '' || currentHash === '#';
      const panel = aiActionsPanelElement ?? document.getElementById('ai-actions-panel');

      // console.log(`Hash changed: ${currentHash}, isOnInbox: ${isOnInbox}`); // Optional debug log

      if (isOnInbox) {
          if (!panel) {
              // console.log("Creating AI Actions Panel..."); // Optional debug log
              createAndInsertAIActionsPanel(); // Create and insert if on inbox and it doesn't exist
          } else {
              // console.log("Showing AI Actions Panel..."); // Optional debug log
              panel.style.display = 'flex'; // Ensure it's visible if it exists
          }
      } else {
          // Not on inbox view
          if (panel) {
              // console.log("Hiding AI Actions Panel..."); // Optional debug log
              panel.style.display = 'none'; // Hide if it exists
          }
      }
  }

  // --- End AI Actions Panel Logic ---

  // --- Initialize Visibility and Listen for Changes ---
  // Initial check when script loads
  // Use a small delay to ensure Gmail UI is likely ready for DOM manipulation
  setTimeout(updateAIActionsVisibility, 500);

  // Listen for hash changes to toggle visibility
  window.addEventListener('hashchange', updateAIActionsVisibility);
  // --- End Initialization ---

  // Add phishing score indicator
  const phishingScoreContainer = document.createElement('div');
  phishingScoreContainer.id = 'phishing-score-container';
  phishingScoreContainer.style.cssText = `
    position: relative;
    background: linear-gradient(145deg, #0a1929, #0d2b3e);
    border: 1px solid rgba(64, 224, 208, 0.1);
    padding: 12px 16px;
    margin: 16px 0px 0px 0px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    width: fit-content;
    max-width: 300px;
  `;

  const topRow = document.createElement('div');
  topRow.style.cssText = `
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  `;

  const scoreIcon = document.createElement('div');
  scoreIcon.style.cssText = `
    width: 20px;
    height: 20px;
    background: rgba(64, 224, 208, 0.1);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  `;
  scoreIcon.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" fill="#40e0d0"/>
    </svg>
  `;

  const scoreTitle = document.createElement('div');
  scoreTitle.style.cssText = `
    color: #ffffff;
    font-weight: 500;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
  `;
  scoreTitle.innerHTML = `
    <span>Phishing Risk Assessment</span>
    <div style="width: 6px; height: 6px; background: #40e0d0; border-radius: 50%; box-shadow: 0 0 8px #40e0d0;"></div>
  `;

  const bottomRow = document.createElement('div');
  bottomRow.style.cssText = `
    display: flex;
    align-items: center;
    gap: 12px;
  `;

  const scoreValue = document.createElement('div');
  scoreValue.style.cssText = `
    color: #40e0d0;
    font-size: 20px;
    font-weight: 600;
  `;
  scoreValue.textContent = '0%';

  const scoreDescription = document.createElement('div');
  scoreDescription.style.cssText = `
    color: #a0a0a0;
    font-size: 13px;
  `;
  scoreDescription.textContent = '';

  topRow.appendChild(scoreIcon);
  topRow.appendChild(scoreTitle);
  bottomRow.appendChild(scoreValue);
  bottomRow.appendChild(scoreDescription);
  phishingScoreContainer.appendChild(topRow);
  phishingScoreContainer.appendChild(bottomRow);

  // Add debouncing and tracking
  let lastProcessedEmailId: string | null = null;
  let processingTimeout: number | null = null;

  // Function to show phishing score - create a new container each time
  function showPhishingScore() {
    // Remove any existing containers first
    document.querySelectorAll('[id="phishing-score-container"]').forEach(container => {
      // Clear any animation interval
      if ((container as HTMLElement).dataset && (container as HTMLElement).dataset.counterInterval) {
        clearInterval(Number((container as HTMLElement).dataset.counterInterval));
        delete (container as HTMLElement).dataset.counterInterval;
      }
      
      // Remove the element and its wrapper if they exist
      if (container.parentElement) {
        container.parentElement.remove();
      } else if (document.body.contains(container)) {
        container.remove();
      }
    });
    
    // Find the email content container
    const emailContent = document.querySelector('div.aHU.hx');
    if (!emailContent) {
      console.log('Email content not found for phishing score');
      return; // No email content found
    }
    
    // Create a NEW phishing score container each time
    // This ensures we're not reusing a container that might have been modified or removed
    const phishingContainer = document.createElement('div');
    phishingContainer.id = 'phishing-score-container';
    phishingContainer.style.cssText = `
      position: relative;
      background: linear-gradient(145deg, #0a1929, #0d2b3e);
      border: 1px solid rgba(64, 224, 208, 0.1);
      padding: 12px 16px;
      margin: 16px 0px 0px 0px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      width: fit-content;
      max-width: 300px;
    `;

    // Create the top row with icon and title
    const topRow = document.createElement('div');
    topRow.style.cssText = `
      display: flex;
      align-items: center; 
      gap: 8px;
      margin-bottom: 4px;
    `;

    const scoreIcon = document.createElement('div');
    scoreIcon.style.cssText = `
      width: 20px;
      height: 20px;
      background: rgba(64, 224, 208, 0.1);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
    `;
    scoreIcon.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" fill="#40e0d0"/>
      </svg>
    `;

    const scoreTitle = document.createElement('div');
    scoreTitle.style.cssText = `
      color: #ffffff;
      font-weight: 500;
      font-size: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
    `;
    scoreTitle.innerHTML = `
      <span>Phishing Risk Assessment</span>
      <div style="width: 6px; height: 6px; background: #40e0d0; border-radius: 50%; box-shadow: 0 0 8px #40e0d0;"></div>
    `;

    // Create the bottom row with score value and description
    const bottomRow = document.createElement('div');
    bottomRow.style.cssText = `
      display: flex;
      align-items: center;
      gap: 12px;
    `;

    // Score value starts at 0%
    const scoreValue = document.createElement('div');
    scoreValue.style.cssText = `
      color: #40e0d0;
      font-size: 20px;
      font-weight: 600;
    `;
    scoreValue.textContent = '0%';

    const scoreDescription = document.createElement('div');
    scoreDescription.style.cssText = `
      color: #a0a0a0;
      font-size: 13px;
    `;
    scoreDescription.textContent = '';

    // Assemble the component
    topRow.appendChild(scoreIcon);
    topRow.appendChild(scoreTitle);
    bottomRow.appendChild(scoreValue);
    bottomRow.appendChild(scoreDescription);
    phishingContainer.appendChild(topRow);
    phishingContainer.appendChild(bottomRow);
    
    // Create a wrapper div for better positioning
    const wrapper = document.createElement('div');
    wrapper.style.cssText = `
      display: flex;
      justify-content: start;
      width: 100%;
      padding-left: 72px;
    `;
    wrapper.appendChild(phishingContainer);
    
    // Add to the DOM
    emailContent.parentNode?.insertBefore(wrapper, emailContent);
    
    // Start animation counter
    let counter = 0;
    const increment = 3; // Speed of counting
    const maxCountTo = 95; // Don't go to 100% while loading
    
    const counterInterval = setInterval(() => {
      counter += increment;
      if (counter >= maxCountTo) {
        counter = maxCountTo; // Cap at maxCountTo while loading
        clearInterval(counterInterval); // Stop incrementing when reached maxCountTo
      }
      scoreValue.textContent = `${counter}%`;
      
      // Change color based on the current count
      let color = '#40e0d0'; // Default teal for low values
      if (counter > 70) {
        color = '#ff4444'; // Red for high values
      } else if (counter > 30) {
        color = '#ffaa00'; // Orange for medium values
      }
      scoreValue.style.color = color;
    }, 80); // Update every 80ms for smooth animation
    
    // Store the interval ID on the score container to clear it later
    phishingContainer.dataset.counterInterval = String(counterInterval);
    
    return phishingContainer; // Return the created container for reference
  }

  // Listen for email opens
  const emailObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.addedNodes.length) {
        const emailContent = document.querySelector('div.gA.gt.acV');
        if (emailContent) {
          // Get the current email ID to track if it's the same email
          const currentEmailId = window.location.hash;
          
          // Only process if it's a different email or if we haven't processed any email yet
          if (currentEmailId !== lastProcessedEmailId) {
            // Clear any existing timeout
            if (processingTimeout) {
              clearTimeout(processingTimeout);
              processingTimeout = null;
            }
            
            // Hide and clean up any existing phishing score containers
            // Use a simple approach that won't interfere with creating new ones
            document.querySelectorAll('[id="phishing-score-container"]').forEach(wrapper => {
              // First hide it immediately to prevent flashing
              (wrapper as HTMLElement).style.display = 'none';
              
              // Clear interval if exists
              if ((wrapper as HTMLElement).dataset && (wrapper as HTMLElement).dataset.counterInterval) {
                clearInterval(Number((wrapper as HTMLElement).dataset.counterInterval));
              }
              
              // Mark for removal
              wrapper.setAttribute('data-remove', 'true');
            });
            
            // Reset the lastProcessedEmailId until we finish processing this one
            lastProcessedEmailId = null;
            
            // Set a new timeout to process the email - adding a delay to ensure UI is ready
            processingTimeout = window.setTimeout(() => {
              // Remove containers marked for removal to ensure clean state
              document.querySelectorAll('[data-remove="true"]').forEach(el => {
                if (el.parentElement) {
                  el.parentElement.remove();
                } else if (document.body.contains(el)) {
                  el.remove();
                }
              });
              
              // Show new phishing score - let's add logging to debug
              console.log('Creating new phishing score');
              const scoreContainer = showPhishingScore();
              console.log('Phishing score created:', scoreContainer);
              
              // Extract email content
              const emailData = extractEmailContent();
              if (emailData) {
                console.log('Email data extracted:', emailData);
                lastProcessedEmailId = currentEmailId;
              }
            }, 300); // Slightly longer delay to ensure UI is ready
          }
        }
      }
    });
  });

  emailObserver.observe(document.body, {
    childList: true,
    subtree: true
  });

  // Add styles for phishing score
  const phishingScoreStyle = document.createElement('style');
  phishingScoreStyle.textContent = `
    #phishing-score-container {
      transition: all 0.3s ease;
    }
    
    #phishing-score-container:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
  `;
  document.head.appendChild(phishingScoreStyle);

  // Add styles for AI actions panel
  const aiActionsStyle = document.createElement('style');
  aiActionsStyle.textContent = `
    #ai-actions-panel {
      scrollbar-width: thin;
      scrollbar-color: rgba(64, 224, 208, 0.2) transparent;
      border-radius: 12px !important;
      overflow: hidden; /* Ensure content doesn't overflow rounded corners */
    }
    
    #ai-actions-panel::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      border-radius: 12px;
      pointer-events: none;
      box-shadow: inset 0 0 0 1px rgba(64, 224, 208, 0.1);
    }
    
    #ai-actions-panel::-webkit-scrollbar {
      width: 6px;
    }
    
    #ai-actions-panel::-webkit-scrollbar-track {
      background: transparent;
      margin: 4px 0; /* Add space at top and bottom */
    }
    
    #ai-actions-panel::-webkit-scrollbar-thumb {
      background-color: rgba(64, 224, 208, 0.2);
      border-radius: 3px;
      border: 2px solid transparent; /* Creates padding effect */
      background-clip: padding-box;
    }
    
    #ai-actions-container {
      scrollbar-width: thin;
      scrollbar-color: rgba(64, 224, 208, 0.2) transparent;
      overflow: auto;
      padding-right: 6px; /* Add padding to prevent content from touching scrollbar */
      margin-right: -6px; /* Offset the padding to maintain alignment */
      border-radius: 8px;
      mask-image: linear-gradient(to bottom, transparent, black 10px, black 90%, transparent 100%);
      -webkit-mask-image: linear-gradient(to bottom, transparent, black 10px, black 90%, transparent 100%);
    }
    
    #ai-actions-container::-webkit-scrollbar {
      height: 6px;
    }
    
    #ai-actions-container::-webkit-scrollbar-track {
      background: transparent;
      margin: 0 4px; /* Add space at left and right */
    }
    
    #ai-actions-container::-webkit-scrollbar-thumb {
      background-color: rgba(64, 224, 208, 0.2);
      border-radius: 3px;
      border: 2px solid transparent; /* Creates padding effect */
      background-clip: padding-box;
    }
    
    #ai-actions-container > div {
      transition: all 0.2s;
      border-radius: 8px;
      overflow: hidden;
    }
    
    #ai-actions-container > div:hover {
      background: rgba(64, 224, 208, 0.15);
      transform: translateY(-2px);
    }

    #toggle-ai-actions:hover {
      background: rgba(64, 224, 208, 0.1);
    }
  `;
  document.head.appendChild(aiActionsStyle);

  // Add function to extract email content
  async function extractEmailContent() {
    // Find the email content container
    const emailContent = document.querySelector('div.aHU.hx');
    if (emailContent) {
      // Get the email content
      const content = emailContent.textContent || '';
      
      // Get other email details
      const subject = document.querySelector('h2.hP')?.textContent || '';
      const sender = document.querySelector('span.gD')?.textContent || '';
      const date = document.querySelector('span.g3')?.textContent || '';
      
      // Create an object with the email data
      const emailData = {
        subject,
        sender,
        date,
        content
      };
      
      try {
        // Send to backend for analysis
        const response = await fetch('http://localhost:8000/analyze-phishing', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(emailData)
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
          // Clear any existing animation interval
          const scoreContainer = document.getElementById('phishing-score-container');
          if (scoreContainer && scoreContainer.dataset.counterInterval) {
            clearInterval(Number(scoreContainer.dataset.counterInterval));
            delete scoreContainer.dataset.counterInterval;
          }
          
          // Update the phishing score display
          if (scoreContainer) {
            const scoreValue = scoreContainer.querySelector('div[style*="font-size: 20px"]');
            if (scoreValue) {
              // Animate to the final score
              const currentScore = parseInt(scoreValue.textContent || '0', 10);
              const targetScore = result.score;
              
              // If the current score is already higher than the target, just set it directly
              if (currentScore >= targetScore) {
                scoreValue.textContent = `${targetScore}%`;
                
                // Update color based on score
                let color = '#40e0d0'; // Default teal
                if (targetScore > 70) {
                  color = '#ff4444'; // Red for high risk
                } else if (targetScore > 30) {
                  color = '#ffaa00'; // Orange for medium risk
                }
                
                (scoreValue as HTMLElement).style.color = color;

                // Add warning message if score is above 60%
                if (targetScore > 60) {
                  addMessage(
                    `⚠️ Warning: This email has a high phishing risk score of ${targetScore}%. Please be cautious and verify the sender's identity before taking any action.`,
                    'bot',
                    'color: #ff4444;'
                  );
                }
              } else {
                // Animate to the final score
                const animateToFinal = setInterval(() => {
                  const current = parseInt(scoreValue.textContent || '0', 10);
                  const newValue = Math.min(current + 5, targetScore);
                  scoreValue.textContent = `${newValue}%`;
                  
                  // Update color based on the current value
                  let color = '#40e0d0'; // Default teal
                  if (newValue > 70) {
                    color = '#ff4444'; // Red for high risk
                  } else if (newValue > 30) {
                    color = '#ffaa00'; // Orange for medium risk
                  }
                  
                  (scoreValue as HTMLElement).style.color = color;
                  
                  if (newValue >= targetScore) {
                    clearInterval(animateToFinal);
                    // Add warning message if score is above 60%
                    if (targetScore > 60) {
                      addMessage(
                        `⚠️ Warning: This email has a high phishing risk score of ${targetScore}%. Please be cautious and verify the sender's identity before taking any action.`,
                        'bot',
                        'color: #ff4444;'
                      );
                    }
                  }
                }, 50);
              }
              
              // Update description
              const description = scoreContainer.querySelector('div[style*="color: #a0a0a0"]');
              if (description) {
                let riskLevel = 'Low';
                if (result.score > 70) {
                  riskLevel = 'High';
                } else if (result.score > 30) {
                  riskLevel = 'Moderate';
                }
                description.textContent = `${riskLevel} risk level detected`;
              }
            }
          }
        }
      } catch (error) {
        console.error('Error analyzing phishing:', error);
        
        // Clear animation and show error in case of failure
        const scoreContainer = document.getElementById('phishing-score-container');
        if (scoreContainer && scoreContainer.dataset.counterInterval) {
          clearInterval(Number(scoreContainer.dataset.counterInterval));
          delete scoreContainer.dataset.counterInterval;
        }
        
        if (scoreContainer) {
          const scoreValue = scoreContainer.querySelector('div[style*="font-size: 20px"]');
          const description = scoreContainer.querySelector('div[style*="color: #a0a0a0"]');
          
          if (scoreValue) {
            scoreValue.textContent = 'N/A';
            (scoreValue as HTMLElement).style.color = '#a0a0a0';
          }
          
          if (description) {
            description.textContent = 'Could not analyze risk level';
          }
        }
      }
      
      return emailData;
    }
    return null;
  }

  // Add WebSocket connection for status updates
  let ws: WebSocket | null = null;

  function connectWebSocket() {
    ws = new WebSocket('ws://localhost:8000/ws/status');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const message = data.message;
      const type = data.type;
      
      // Style message based on type
      let style = '';
      switch(type) {
        case 'success':
          style = 'color: #00ff9d;';
          break;
        case 'error':
          style = 'color: #ff4444;';
          break;
        case 'warning':
          style = 'color: #ffffff;';
          break;
        default:
          style = 'color: #ffffff;';
      }
      
      addMessage(message, 'bot', style);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
      // Attempt to reconnect after 5 seconds
      setTimeout(connectWebSocket, 5000);
    };
  }

  // Connect WebSocket when content script loads
  connectWebSocket();

  // Function to add messages to the chat
  function addMessage(text: string, sender: 'user' | 'bot', style: string = '', tooltip?: string) {
    const messageDiv = document.createElement('div');
    messageDiv.style.cssText = `
      padding: 10px 14px;
      border-radius: 12px;
      max-width: 80%;
      word-wrap: break-word;
      font-size: 14px;
      line-height: 1.4;
      ${sender === 'user' 
        ? 'background: #00ff9d; color: #1a1a1a; align-self: flex-end;' 
        : 'background: #2a2a2a; color: #ffffff; align-self: flex-start;'}
      box-shadow: 0 1px 2px rgba(0,0,0,0.2);
      ${style}
      display: flex;
      align-items: center;
      gap: 8px;
    `;

    const textSpan = document.createElement('span');
    textSpan.textContent = text;
    messageDiv.appendChild(textSpan);

    if (tooltip) {
      const tooltipButton = document.createElement('button');
      tooltipButton.innerHTML = '?';
      tooltipButton.style.cssText = `
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.1);
        border: none;
        color: white;
        font-size: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s;
      `;

      const tooltipDiv = document.createElement('div');
      tooltipDiv.textContent = tooltip;
      tooltipDiv.style.cssText = `
        position: absolute;
        background: rgba(0, 0, 0, 0.9);
        color: white;
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 12px;
        max-width: 300px;
        z-index: 10000;
        display: none;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
      `;

      tooltipButton.addEventListener('mouseenter', () => {
        tooltipDiv.style.display = 'block';
        const rect = tooltipButton.getBoundingClientRect();
        tooltipDiv.style.top = `${rect.top - tooltipDiv.offsetHeight - 10}px`;
        tooltipDiv.style.left = `${rect.left}px`;
      });

      tooltipButton.addEventListener('mouseleave', () => {
        tooltipDiv.style.display = 'none';
      });

      messageDiv.appendChild(tooltipButton);
      document.body.appendChild(tooltipDiv);
    }

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return messageDiv;
  }

  // Add welcome message
  addMessage('Hello! I\'m your AI Email Assistant. I\'ll help you manage your emails efficiently.', 'bot');
}