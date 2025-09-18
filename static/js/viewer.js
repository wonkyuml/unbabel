document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const statusLight = document.getElementById('status-light');
  const statusText = document.getElementById('status-text');
  const captionsOriginal = document.querySelector('#captions-original .captions-content');
  const captionsTranslated = document.querySelector('#captions-translated .captions-content');
  const autoScrollButton = document.getElementById('auto-scroll');
  const clearCaptionsButton = document.getElementById('clear-captions');
  const roomId = document.querySelector('meta[name="room-id"]').getAttribute('content');

  // Get the parent elements that have scrollbars
  const originalContainer = document.querySelector('#captions-original');
  const translatedContainer = document.querySelector('#captions-translated');

  // State variables
  let websocket = null;
  let autoScroll = true;
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 10;
  const reconnectDelay = 1000;
  const captionHistory = [];
  const maxCaptionHistory = 100;
  
  // Set up MutationObserver to detect when new content is added
  const observerOptions = {
    childList: true,
    subtree: true
  };
  
  // Create observers for both caption containers
  const originalObserver = new MutationObserver(() => {
    if (autoScroll && originalContainer) {
      console.log('MutationObserver triggered for original');
      originalContainer.scrollTop = originalContainer.scrollHeight;
    }
  });
  
  const translatedObserver = new MutationObserver(() => {
    if (autoScroll && translatedContainer) {
      console.log('MutationObserver triggered for translated');
      translatedContainer.scrollTop = translatedContainer.scrollHeight;
    }
  });
  
  // Start observing
  if (originalContainer) {
    originalObserver.observe(captionsOriginal, observerOptions);
    console.log('Started observing original container');
  }
  
  if (translatedContainer) {
    translatedObserver.observe(captionsTranslated, observerOptions);
    console.log('Started observing translated container');
  }

  // WebSocket setup
  let pingInterval;
  let reconnectTimeout;
  let lastPongTime = 0;
  const pingIntervalTime = 30000; // 30 seconds between pings
  const pongTimeoutTime = 10000;  // 10 seconds to wait for pong response
  
  function setupWebSocket() {
    // Clear any existing timers
    clearPingInterval();
    clearTimeout(reconnectTimeout);
    
    // Close existing connection if any
    if (websocket && websocket.readyState !== WebSocket.CLOSED) {
      websocket.close();
    }

    // Create new WebSocket connection
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/view/${roomId}`;
    
    console.log(`Connecting to WebSocket at ${wsUrl}`);
    websocket = new WebSocket(wsUrl);

    // WebSocket event handlers
    websocket.onopen = () => {
      console.log('WebSocket connection established');
      updateStatus('connected', 'Connected');
      reconnectAttempts = 0;
      
      // Start ping interval once connected
      startPingInterval();
      
      // Record initial pong time
      lastPongTime = Date.now();
    };

    websocket.onclose = (event) => {
      console.log('WebSocket connection closed', event.code, event.reason);
      updateStatus('disconnected', 'Disconnected');
      
      // Clean up
      clearPingInterval();
      
      // Use exponential backoff for reconnection
      if (reconnectAttempts < maxReconnectAttempts) {
        const delay = Math.min(reconnectDelay * Math.pow(1.5, reconnectAttempts), 30000); // Max 30 seconds
        reconnectAttempts++;
        updateStatus('connecting', `Reconnecting (${reconnectAttempts}/${maxReconnectAttempts}) in ${Math.round(delay/1000)}s...`);
        
        // Schedule reconnection
        reconnectTimeout = setTimeout(setupWebSocket, delay);
      } else {
        updateStatus('disconnected', 'Failed to reconnect');
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      updateStatus('disconnected', 'Connection error');
      // Don't attempt to reconnect here - let onclose handle it
    };

    websocket.onmessage = (event) => {
      try {
        // Update last pong time on any message
        lastPongTime = Date.now();
        
        // Handle ping message specially
        if (event.data === 'ping') {
          console.log('Received ping, sending pong');
          if (websocket.readyState === WebSocket.OPEN) {
            websocket.send('pong');
          }
          return;
        }
        
        // Handle pong message
        if (event.data === 'pong') {
          console.log('Received pong');
          return;
        }
        
        // Handle normal messages
        const message = JSON.parse(event.data);
        handleMessage(message);
      } catch (error) {
        console.error('Error handling message:', error, event.data);
      }
    };
  }
  
  // Start ping interval
  function startPingInterval() {
    clearPingInterval(); // Clear any existing interval
    
    pingInterval = setInterval(() => {
      // Check if connection is still alive
      if (Date.now() - lastPongTime > pongTimeoutTime) {
        console.warn('No pong received in time, reconnecting...');
        if (websocket) websocket.close();
        return;
      }
      
      // Send ping if connection is open
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        console.log('Sending ping');
        websocket.send('ping');
      }
    }, pingIntervalTime);
  }
  
  // Clear ping interval
  function clearPingInterval() {
    if (pingInterval) {
      clearInterval(pingInterval);
      pingInterval = null;
    }
  }

  // Handle incoming messages
  function handleMessage(message) {
    console.log('Received message:', message);

    switch (message.type) {
      case 'connection_established':
        updateStatus('connected', 'Connected');
        break;
        
      case 'caption':
        // Add caption to history
        captionHistory.push(message);
        if (captionHistory.length > maxCaptionHistory) {
          captionHistory.shift(); // Remove oldest caption
        }
        
        // Display caption
        displayCaption(message);
        break;
        
      case 'error':
        console.error('Error from server:', message.message);
        showError(message.message);
        break;
    }
  }

  // Update connection status
  function updateStatus(state, text) {
    statusLight.className = 'status-light ' + state;
    statusText.textContent = text;
  }

  // Display caption
  function displayCaption(caption) {
    // Create caption elements
    const originalDiv = createCaptionElement(caption.original, caption.ts);
    const translatedDiv = createCaptionElement(caption.translation, caption.ts);
    
    // Add to containers
    captionsOriginal.appendChild(originalDiv);
    captionsTranslated.appendChild(translatedDiv);
    
    // Auto-scroll if enabled
    if (autoScroll) {
      scrollCaptionsToBottom();
    }
  }
  
  // Dedicated function to handle scrolling
  function scrollCaptionsToBottom() {
    // Try multiple approaches to ensure scrolling works
    
    // Approach 1: Direct scrolling on content elements
    captionsOriginal.scrollTop = 999999;
    captionsTranslated.scrollTop = 999999;
    
    // Approach 2: Scroll the parent containers
    if (originalContainer) originalContainer.scrollTop = 999999;
    if (translatedContainer) translatedContainer.scrollTop = 999999;
    
    // Approach 3: Delayed scrolling to ensure DOM is updated
    setTimeout(() => {
      captionsOriginal.scrollTop = 999999;
      captionsTranslated.scrollTop = 999999;
      
      if (originalContainer) originalContainer.scrollTop = 999999;
      if (translatedContainer) translatedContainer.scrollTop = 999999;
      
      console.log('Scrolled to bottom (delayed)');
    }, 50);
  }

  // Create caption element
  function createCaptionElement(text, timestamp) {
    const div = document.createElement('div');
    div.className = 'caption-item';
    
    const textElement = document.createElement('div');
    textElement.className = 'caption-text';
    textElement.textContent = text;
    
    const timeElement = document.createElement('div');
    timeElement.className = 'caption-timestamp';
    
    // Format timestamp - use current time instead of asyncio timestamp
    const date = new Date();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    timeElement.textContent = `${hours}:${minutes}:${seconds}`;
    
    div.appendChild(textElement);
    div.appendChild(timeElement);
    
    return div;
  }

  // Show error message
  function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    document.querySelector('.viewer-container').prepend(errorDiv);
    
    // Remove after 5 seconds
    setTimeout(() => {
      errorDiv.remove();
    }, 5000);
  }

  // Toggle auto-scroll
  function toggleAutoScroll() {
    autoScroll = !autoScroll;
    autoScrollButton.textContent = `Auto-scroll: ${autoScroll ? 'ON' : 'OFF'}`;
    autoScrollButton.classList.toggle('active', autoScroll);
    
    if (autoScroll) {
      // Use our dedicated scrolling function
      scrollCaptionsToBottom();
    }
  }

  // Clear captions
  function clearCaptions() {
    captionsOriginal.innerHTML = '';
    captionsTranslated.innerHTML = '';
    captionHistory.length = 0;
  }

  // Toggle view function for mobile
  function toggleView() {
    const captionsBox = document.querySelector('.captions-box');
    const originalCaption = document.querySelector('#captions-original');
    const translatedCaption = document.querySelector('#captions-translated');
    
    // Check current order
    const currentOrder = window.getComputedStyle(translatedCaption).order;
    
    if (currentOrder === '1' || currentOrder === '') {
      // Currently translated is first, switch to original first
      translatedCaption.style.order = '2';
      originalCaption.style.order = '1';
      document.querySelector('#toggle-view').textContent = 'Show Translation First';
    } else {
      // Currently original is first, switch to translated first
      translatedCaption.style.order = '1';
      originalCaption.style.order = '2';
      document.querySelector('#toggle-view').textContent = 'Show Original First';
    }
    
    // Re-scroll if auto-scroll is on
    if (autoScroll) {
      scrollCaptionsToBottom();
    }
  }
  
  // Event listeners
  autoScrollButton.addEventListener('click', toggleAutoScroll);
  clearCaptionsButton.addEventListener('click', clearCaptions);
  document.getElementById('toggle-view').addEventListener('click', toggleView);

  // Initialize WebSocket connection
  setupWebSocket();

  // Handle page visibility changes to reconnect if needed
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && 
        (!websocket || websocket.readyState !== WebSocket.OPEN)) {
      setupWebSocket();
    }
  });
});
