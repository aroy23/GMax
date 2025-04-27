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
    height: 500px;
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

  // Create input container
  const inputContainer = document.createElement('div');
  inputContainer.style.cssText = `
    padding: 12px;
    background: linear-gradient(145deg, #0d2b3e, #0a1929);
    border-top: 1px solid rgba(64, 224, 208, 0.1);
    display: flex;
    gap: 8px;
  `;

  const input = document.createElement('input');
  input.type = 'text';
  input.placeholder = 'Ask me anything...';
  input.style.cssText = `
    flex: 1;
    padding: 10px 12px;
    border: 1px solid rgba(64, 224, 208, 0.2);
    border-radius: 8px;
    outline: none;
    font-size: 14px;
    background: rgba(10, 25, 41, 0.5);
    color: #ffffff;
    transition: all 0.2s;
  `;
  input.addEventListener('focus', () => {
    input.style.borderColor = '#40e0d0';
    input.style.boxShadow = '0 0 0 2px rgba(64, 224, 208, 0.2)';
  });
  input.addEventListener('blur', () => {
    input.style.borderColor = 'rgba(64, 224, 208, 0.2)';
    input.style.boxShadow = 'none';
  });

  const sendButton = document.createElement('button');
  sendButton.innerHTML = `
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" fill="#40e0d0"/>
    </svg>
  `;
  sendButton.style.cssText = `
    padding: 8px;
    background: rgba(64, 224, 208, 0.1);
    color: white;
    border: 1px solid rgba(64, 224, 208, 0.2);
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
  `;
  sendButton.addEventListener('mouseover', () => {
    sendButton.style.background = 'rgba(64, 224, 208, 0.2)';
    sendButton.style.borderColor = 'rgba(64, 224, 208, 0.3)';
    sendButton.style.boxShadow = '0 0 12px rgba(64, 224, 208, 0.2)';
  });
  sendButton.addEventListener('mouseout', () => {
    sendButton.style.background = 'rgba(64, 224, 208, 0.1)';
    sendButton.style.borderColor = 'rgba(64, 224, 208, 0.2)';
    sendButton.style.boxShadow = 'none';
  });

  // Assemble the chatbox
  inputContainer.appendChild(input);
  inputContainer.appendChild(sendButton);
  chatboxContainer.appendChild(header);
  chatboxContainer.appendChild(messagesContainer);
  chatboxContainer.appendChild(inputContainer);
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
      chatboxContainer.style.height = isMinimized ? '500px' : '60px';
      
      if (isMinimized) {
        // Expanding
        messagesContainer.style.display = 'flex';
        inputContainer.style.display = 'flex';
        chatboxContainer.style.background = 'linear-gradient(145deg, #0a1929, #0d2b3e)';
      } else {
        // Collapsing
        messagesContainer.style.display = 'none';
        inputContainer.style.display = 'none';
        chatboxContainer.style.background = 'linear-gradient(145deg, #0a1929, #0d2b3e)';
      }
      
      minimizeButton.textContent = isMinimized ? '−' : '+';
    });
  }

  // Handle sending messages
  sendButton.addEventListener('click', () => {
    const message = input.value.trim();
    if (message) {
      addMessage(message, 'user');
      input.value = '';
      processUserMessage(message);
    }
  });

  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      sendButton.click();
    }
  });

  // Function to add messages to the chat
  function addMessage(text: string, sender: 'user' | 'bot') {
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
    `;
    messageDiv.textContent = text;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return messageDiv;
  }

  // Function to process user messages
  function processUserMessage(message: string) {
    // TODO: Implement message processing logic
    // For now, just echo the message
    setTimeout(() => {
      addMessage(`You said: "${message}"`, 'bot');
    }, 500);
  }

  // Add welcome message
  addMessage('Hello! I\'m your AI Email Assistant. How can I help you today?', 'bot');

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
          <div style="font-weight: 500; margin-bottom: 4px; color: #ffffff;">Auto-respond to Important Emails</div>
          <div style="color: #a0a0a0; font-size: 14px;">Automatically respond to emails marked as important</div>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" checked>
          <span class="toggle-slider"></span>
        </label>
      </div>
      
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px; background: rgba(10, 25, 41, 0.5); border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(64, 224, 208, 0.1);">
        <div style="flex: 1;">
          <div style="font-weight: 500; margin-bottom: 4px; color: #ffffff;">Smart Email Categorization</div>
          <div style="color: #a0a0a0; font-size: 14px;">Automatically categorize incoming emails</div>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" checked>
          <span class="toggle-slider"></span>
        </label>
      </div>
    </div>

    <div style="margin-bottom: 32px;">
      <h2 style="color: #40e0d0; margin: 0 0 16px 0; font-size: 18px;">Automation</h2>
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px; background: rgba(10, 25, 41, 0.5); border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(64, 224, 208, 0.1);">
        <div style="flex: 1;">
          <div style="font-weight: 500; margin-bottom: 4px; color: #ffffff;">Schedule Email Sending</div>
          <div style="color: #a0a0a0; font-size: 14px;">Automatically schedule emails for optimal delivery times</div>
        </div>
        <label class="toggle-switch">
          <input type="checkbox">
          <span class="toggle-slider"></span>
        </label>
      </div>
      
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px; background: rgba(10, 25, 41, 0.5); border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(64, 224, 208, 0.1);">
        <div style="flex: 1;">
          <div style="font-weight: 500; margin-bottom: 4px; color: #ffffff;">Follow-up Reminders</div>
          <div style="color: #a0a0a0; font-size: 14px;">Set automatic reminders for unanswered emails</div>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" checked>
          <span class="toggle-slider"></span>
        </label>
      </div>
    </div>

    <div style="margin-bottom: 32px;">
      <h2 style="color: #40e0d0; margin: 0 0 16px 0; font-size: 18px;">Privacy & Security</h2>
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px; background: rgba(10, 25, 41, 0.5); border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(64, 224, 208, 0.1);">
        <div style="flex: 1;">
          <div style="font-weight: 500; margin-bottom: 4px; color: #ffffff;">Data Collection</div>
          <div style="color: #a0a0a0; font-size: 14px;">Allow anonymous usage data collection</div>
        </div>
        <label class="toggle-switch">
          <input type="checkbox">
          <span class="toggle-slider"></span>
        </label>
      </div>
      
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px; background: rgba(10, 25, 41, 0.5); border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(64, 224, 208, 0.1);">
        <div style="flex: 1;">
          <div style="font-weight: 500; margin-bottom: 4px; color: #ffffff;">Secure Mode</div>
          <div style="color: #a0a0a0; font-size: 14px;">Enable additional security measures</div>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" checked>
          <span class="toggle-slider"></span>
        </label>
      </div>
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

  // Update settings button functionality
  const settingsButton = document.getElementById('settings-button');
  if (settingsButton) {
    settingsButton.addEventListener('click', () => {
      settingsOverlay.style.display = 'flex';
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
      addMessage('Persona Trained Successfully!', 'bot');
    } catch (error) {
      console.error('Error fetching data:', error);
      clearInterval(loadingInterval);
      addMessage('Error training persona. Please try again.', 'bot');
    }
  }

  retrainButton.addEventListener('click', () => {
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

  smartSortButton.addEventListener('click', () => {
    // TODO: Implement smart sort functionality
    console.log('Smart Sort clicked');
  });

  quickActionsPanel.appendChild(retrainButton);
  quickActionsPanel.appendChild(smartSortButton);
  document.body.appendChild(quickActionsPanel);

  // Create AI actions panel
  const aiActionsPanel = document.createElement('div');
  aiActionsPanel.id = 'ai-actions-panel';
  aiActionsPanel.style.cssText = `
    position: relative;
    background: linear-gradient(145deg, #0a1929, #0d2b3e);
    border: 1px solid rgba(64, 224, 208, 0.1);
    padding: 8px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 200px;
    overflow-y: auto;
    width: calc(100% - 200px);
    margin: 8px 16px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
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

  // Create actions container with initial collapsed state
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

  // Find the AO div and insert the panel before it
  const aoDiv = document.querySelector('div.AO');
  if (aoDiv) {
    aoDiv.parentNode?.insertBefore(aiActionsPanel, aoDiv);
    setupToggleFunctionality();
  } else {
    // If AO div not found, try to find it after a short delay (Gmail might still be loading)
    setTimeout(() => {
      const aoDiv = document.querySelector('div.AO');
      if (aoDiv) {
        aoDiv.parentNode?.insertBefore(aiActionsPanel, aoDiv);
        setupToggleFunctionality();
      } else {
        console.error('Could not find AO div for AI actions panel placement');
      }
    }, 1000);
  }

  // Function to setup toggle functionality
  function setupToggleFunctionality() {
    const toggleButton = document.getElementById('toggle-ai-actions');
    if (toggleButton) {
      toggleButton.addEventListener('click', (e) => {
        e.stopPropagation();
        const isCollapsed = actionsContainer.style.maxHeight === '0px';
        
        if (isCollapsed) {
          actionsContainer.style.maxHeight = '200px';
          actionsContainer.style.opacity = '1';
          actionsContainer.style.padding = '4px 0';
          toggleButton.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M7 10l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          `;
        } else {
          actionsContainer.style.maxHeight = '0px';
          actionsContainer.style.opacity = '0';
          actionsContainer.style.padding = '0';
          toggleButton.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M7 14l5-5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          `;
        }
      });

      // Add click handler to header for toggling
      aiActionsHeader.addEventListener('click', (e) => {
        if (e.target !== toggleButton) {
          toggleButton.click();
        }
      });
    }
  }

  // Function to add a new action
  function addAIAction(action: string, timestamp: Date) {
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
    
    const timeString = timestamp.toLocaleTimeString();
    actionElement.innerHTML = `
      <div style="color: #40e0d0; font-size: 12px;">${timeString}</div>
      <div style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${action}</div>
    `;

    actionsContainer.insertBefore(actionElement, actionsContainer.firstChild);
    
    // Limit to 5 actions
    if (actionsContainer.children.length > 5) {
      actionsContainer.removeChild(actionsContainer.lastChild!);
    }
  }

  // Example usage:
  addAIAction('Analyzed email content for sentiment', new Date());
  addAIAction('Generated response draft', new Date());
  addAIAction('Suggested email categorization', new Date());

  // Add styles for quick actions panel
  const quickActionsStyle = document.createElement('style');
  quickActionsStyle.textContent = `
    #quick-actions-panel {
      min-width: 120px;
    }
    
    #quick-actions-panel button {
      white-space: nowrap;
    }
    
    #quick-actions-panel button:hover {
      transform: translateY(-1px);
    }
  `;
  document.head.appendChild(quickActionsStyle);

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
  scoreValue.textContent = '50%';

  const scoreDescription = document.createElement('div');
  scoreDescription.style.cssText = `
    color: #a0a0a0;
    font-size: 13px;
  `;
  scoreDescription.textContent = 'Moderate risk level detected';

  topRow.appendChild(scoreIcon);
  topRow.appendChild(scoreTitle);
  bottomRow.appendChild(scoreValue);
  bottomRow.appendChild(scoreDescription);
  phishingScoreContainer.appendChild(topRow);
  phishingScoreContainer.appendChild(bottomRow);

  // Function to show phishing score
  function showPhishingScore() {
    const emailContent = document.querySelector('div.aHU.hx');
    if (emailContent) {
      // Create a wrapper div for better positioning
      const wrapper = document.createElement('div');
      wrapper.style.cssText = `
        display: flex;
        justify-content: start;
        width: 100%;
        padding-left: 72px;
      `;
      wrapper.appendChild(phishingScoreContainer);
      emailContent.parentNode?.insertBefore(wrapper, emailContent);
    }
  }

  // Listen for email opens
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.addedNodes.length) {
        const emailContent = document.querySelector('div.gA.gt.acV');
        if (emailContent && !document.getElementById('phishing-score-container')) {
          showPhishingScore();
        }
      }
    });
  });

  observer.observe(document.body, {
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
    }
    
    #ai-actions-panel::-webkit-scrollbar-thumb {
      background-color: rgba(64, 224, 208, 0.2);
      border-radius: 3px;
    }
    
    #ai-actions-container {
      scrollbar-width: thin;
      scrollbar-color: rgba(64, 224, 208, 0.2) transparent;
      overflow: hidden;
    }
    
    #ai-actions-container::-webkit-scrollbar {
      height: 6px;
    }
    
    #ai-actions-container::-webkit-scrollbar-track {
      background: transparent;
    }
    
    #ai-actions-container::-webkit-scrollbar-thumb {
      background-color: rgba(64, 224, 208, 0.2);
      border-radius: 3px;
    }
    
    #ai-actions-container > div {
      transition: all 0.2s;
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
}