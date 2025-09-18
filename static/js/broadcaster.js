document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const startButton = document.getElementById('start-broadcast');
  const stopButton = document.getElementById('stop-broadcast');
  const statusLight = document.getElementById('status-light');
  const statusText = document.getElementById('status-text');
  const connectionStatus = document.getElementById('connection-status');
  const latencyElement = document.getElementById('latency');
  const viewerCountElement = document.getElementById('viewer-count');
  const transcriptOriginal = document.querySelector('#transcript-original .transcript-content');
  const transcriptTranslated = document.querySelector('#transcript-translated .transcript-content');
  const viewerUrlInput = document.getElementById('viewer-url');
  const copyViewerUrlButton = document.getElementById('copy-viewer-url');
  const copyLinkButton = document.getElementById('copy-link');
  const microphoneSelect = document.getElementById('microphone-select'); // Added for microphone selection
  const roomId = document.querySelector('meta[name="room-id"]').getAttribute('content');

  // State variables
  let websocket = null;
  let mediaRecorder = null;
  let audioContext = null;
  let audioStream = null;
  let isRecording = false;
  let lastTimestamp = 0;
  let viewerCount = 0;
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 5;
  const reconnectDelay = 1000;

  // Set viewer URL
  const viewerUrl = `${window.location.origin}/view/${roomId}`;
  viewerUrlInput.value = viewerUrl;

  // Populate microphone list
  async function populateMicrophoneList() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
      console.warn("enumerateDevices() not supported.");
      microphoneSelect.style.display = 'none'; // Hide select if not supported
      return;
    }

    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioInputDevices = devices.filter(device => device.kind === 'audioinput');
      
      microphoneSelect.innerHTML = ''; // Clear existing options

      if (audioInputDevices.length === 0) {
        console.warn("No audio input devices found.");
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No microphones found';
        microphoneSelect.appendChild(option);
        microphoneSelect.disabled = true;
        return;
      }

      audioInputDevices.forEach((device, index) => {
        const option = document.createElement('option');
        option.value = device.deviceId;
        option.textContent = device.label || `Microphone ${index + 1}`;
        microphoneSelect.appendChild(option);
      });
      microphoneSelect.disabled = false;
    } catch (err) {
      console.error('Error enumerating devices:', err);
      showError(`Error listing microphones: ${err.message}`);
      microphoneSelect.style.display = 'none';
    }
  }

  // Initial population of microphone list
  populateMicrophoneList();
  // Repopulate if devices change (e.g. USB mic plugged in/out)
  navigator.mediaDevices.ondevicechange = populateMicrophoneList;

  // WebSocket setup
  function setupWebSocket() {
    // Close existing connection if any
    if (websocket) {
      websocket.close();
    }

    // Create new WebSocket connection
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/stream/${roomId}`;
    websocket = new WebSocket(wsUrl);

    // WebSocket event handlers
    websocket.onopen = () => {
      console.log('WebSocket connection established');
      updateStatus('connected', 'Connected');
      reconnectAttempts = 0;
    };

    websocket.onclose = (event) => {
      console.log('WebSocket connection closed', event);
      updateStatus('disconnected', 'Disconnected');
      
      // Attempt to reconnect
      if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        updateStatus('connecting', `Reconnecting (${reconnectAttempts}/${maxReconnectAttempts})...`);
        setTimeout(setupWebSocket, reconnectDelay * reconnectAttempts);
      } else {
        updateStatus('disconnected', 'Failed to reconnect');
        stopRecording();
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      updateStatus('disconnected', 'Connection error');
    };

    websocket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        handleMessage(message);
      } catch (error) {
        console.error('Error parsing message:', error);
      }
    };
  }

  // Handle incoming messages
  function handleMessage(message) {
    console.log('Received message:', message);

    switch (message.type) {
      case 'connection_established':
        updateStatus('connected', 'Connected');
        break;
        
      case 'caption':
        // Calculate latency
        const now = Date.now() / 1000;
        const latency = (now - message.ts).toFixed(2);
        latencyElement.textContent = `${latency}s`;
        
        // Update transcripts
        appendTranscript(transcriptOriginal, message.original);
        appendTranscript(transcriptTranslated, message.translation);
        break;
        
      case 'viewer_count':
        viewerCount = message.count;
        viewerCountElement.textContent = viewerCount;
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
    connectionStatus.textContent = text;
  }

  // Append transcript to container
  function appendTranscript(container, text) {
    const p = document.createElement('p');
    p.textContent = text;
    container.appendChild(p);
    container.scrollTop = container.scrollHeight;
  }

  // Show error message
  function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    document.querySelector('.broadcast-container').prepend(errorDiv);
    
    // Remove after 5 seconds
    setTimeout(() => {
      errorDiv.remove();
    }, 5000);
  }

  // Start recording audio
  async function startRecording() {
    if (microphoneSelect.value === '' && microphoneSelect.options.length > 0 && microphoneSelect.options[0].textContent !== 'No microphones found') {
        showError('Please select a microphone.');
        return;
    }
    if (microphoneSelect.disabled || microphoneSelect.options.length === 0) {
        showError('No microphone available or selection is disabled.');
        return;
    }

    try {
      const selectedDeviceId = microphoneSelect.value;
      const audioConstraints = {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      };

      if (selectedDeviceId) {
        audioConstraints.deviceId = { exact: selectedDeviceId };
      }

      // Request microphone access with specific deviceId if selected
      audioStream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
      
      // Create audio context with proper sample rate for speech recognition
      audioContext = new AudioContext({
        sampleRate: 16000,  // 16kHz is optimal for speech recognition
      });
      
      // Create media recorder with specific options for Deepgram compatibility
      const options = {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 16000
      };
      
      mediaRecorder = new MediaRecorder(audioStream, options);
      
      // Set up WebSocket connection
      setupWebSocket();
      
      // Handle data available event
      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0 && websocket && websocket.readyState === WebSocket.OPEN) {
          try {
            // Convert blob to ArrayBuffer
            const arrayBuffer = await event.data.arrayBuffer();
            
            // Log the audio data being sent
            console.log(`Sending audio chunk: ${arrayBuffer.byteLength} bytes`);
            
            // Send audio data to server
            websocket.send(arrayBuffer);
          } catch (error) {
            console.error('Error sending audio data:', error);
          }
        }
      };
      
      // Start recording with larger chunks for better speech recognition
      mediaRecorder.start(2000); // Collect 2000ms (2 second) chunks for better transcription
      isRecording = true;
      
      // Update UI
      startButton.disabled = true;
      stopButton.disabled = false;
      updateStatus('connected', 'Broadcasting');
      
    } catch (error) {
      console.error('Error starting recording:', error);
      showError(`Could not access microphone: ${error.message}`);
    }
  }

  // Stop recording audio
  function stopRecording() {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      isRecording = false;
      
      // Stop all tracks
      if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
      }
      
      // Close audio context
      if (audioContext) {
        audioContext.close();
      }
      
      // Update UI
      startButton.disabled = false;
      stopButton.disabled = true;
      updateStatus('disconnected', 'Stopped');
    }
    
    // Close WebSocket connection
    if (websocket) {
      websocket.close();
    }
  }

  // Copy viewer URL to clipboard
  function copyViewerUrl() {
    viewerUrlInput.select();
    document.execCommand('copy');
    
    // Show feedback
    copyViewerUrlButton.textContent = 'Copied!';
    setTimeout(() => {
      copyViewerUrlButton.textContent = 'Copy';
    }, 2000);
  }

  // Event listeners
  startButton.addEventListener('click', startRecording);
  stopButton.addEventListener('click', stopRecording);
  copyViewerUrlButton.addEventListener('click', copyViewerUrl);
  copyLinkButton.addEventListener('click', copyViewerUrl);

  // Handle page unload
  window.addEventListener('beforeunload', () => {
    stopRecording();
  });
});
