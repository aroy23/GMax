chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed');
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((message, _, sendResponse) => {
  if (message.type === 'openSettings') {
    // This is no longer needed as we're using an overlay
    sendResponse({ success: true });
  }
}); 