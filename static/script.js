document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();
    
    // Elements
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const micButton = document.getElementById('mic-button');
    const chatMessages = document.getElementById('chat-messages');
    const recordingIndicator = document.getElementById('recording-indicator');
    const calendarEvents = document.getElementById('events-list');
    const memorySearch = document.getElementById('memory-search');
    const memorySearchBtn = document.getElementById('memory-search-btn');
    const memoryResults = document.getElementById('memory-results');
    const memorySaveBtn = document.getElementById('memory-save-btn');
    const memoryKey = document.getElementById('memory-key');
    const memoryValue = document.getElementById('memory-value');
    
    // Status elements
    const versionInfo = document.getElementById('version-info');
    const openaiStatus = document.getElementById('openai-status');
    const calendarStatusInfo = document.getElementById('calendar-status-info');
    const voiceStatus = document.getElementById('voice-status');
    
    // Variables
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;
    
    // Check health status on load
    checkHealth();
    
    // Load calendar events if on calendar tab
    document.querySelector('a[href="#calendar-tab"]').addEventListener('click', function() {
        loadCalendarEvents();
    });
    
    // Send message function
    function sendMessage() {
        const message = messageInput.value.trim();
        if (message) {
            // Add user message to chat
            addMessage(message, 'user');
            
            // Clear input field
            messageInput.value = '';
            
            // Show typing indicator
            showTypingIndicator();
            
            // Send to the API
            fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: message })
            })
            .then(response => response.json())
            .then(data => {
                // Remove typing indicator
                removeTypingIndicator();
                
                // Add response to chat
                addMessage(data.response, 'system');
            })
            .catch(error => {
                console.error('Error:', error);
                removeTypingIndicator();
                addMessage('Sorry, there was an error processing your request.', 'system');
            });
        }
    }
    
    // Add message to chat
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Support markdown-style formatting
        text = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
        
        contentDiv.innerHTML = `<p>${text}</p>`;
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        const now = new Date();
        timeDiv.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        contentDiv.appendChild(timeDiv);
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Show typing indicator
    function showTypingIndicator() {
        const indicatorDiv = document.createElement('div');
        indicatorDiv.className = 'message system-message';
        indicatorDiv.id = 'typing-indicator';
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.innerHTML = '<span></span><span></span><span></span>';
        
        indicatorDiv.appendChild(typingDiv);
        chatMessages.appendChild(indicatorDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Remove typing indicator
    function removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    // Handle voice recording
    function toggleRecording() {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    }
    
    // Start voice recording
    function startRecording() {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.addEventListener('dataavailable', event => {
                    audioChunks.push(event.data);
                });
                
                mediaRecorder.addEventListener('stop', () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    
                    // Show a temporary message
                    addMessage('Processing audio...', 'system');
                    
                    // Send to the API for transcription
                    const formData = new FormData();
                    formData.append('audio', audioBlob);
                    
                    fetch('/voice/transcribe', {
                        method: 'POST',
                        body: audioBlob
                    })
                    .then(response => response.json())
                    .then(data => {
                        // Remove the processing message
                        chatMessages.removeChild(chatMessages.lastChild);
                        
                        // Add the transcribed text as a user message
                        if (data.text) {
                            addMessage(data.text, 'user');
                            
                            // Now send the transcribed text to the AI
                            showTypingIndicator();
                            
                            fetch('/ask', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ prompt: data.text })
                            })
                            .then(response => response.json())
                            .then(data => {
                                removeTypingIndicator();
                                addMessage(data.response, 'system');
                            })
                            .catch(error => {
                                console.error('Error:', error);
                                removeTypingIndicator();
                                addMessage('Sorry, there was an error processing your request.', 'system');
                            });
                        } else {
                            addMessage('Sorry, I couldn\'t understand the audio.', 'system');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        // Remove the processing message
                        chatMessages.removeChild(chatMessages.lastChild);
                        addMessage('Sorry, there was an error processing the audio.', 'system');
                    });
                    
                    stream.getTracks().forEach(track => track.stop());
                });
                
                mediaRecorder.start();
                isRecording = true;
                recordingIndicator.classList.remove('d-none');
                micButton.classList.add('btn-danger');
                micButton.classList.remove('btn-outline-secondary');
            })
            .catch(error => {
                console.error('Error accessing microphone:', error);
                addMessage('Sorry, I couldn\'t access your microphone.', 'system');
            });
    }
    
    // Stop voice recording
    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            recordingIndicator.classList.add('d-none');
            micButton.classList.remove('btn-danger');
            micButton.classList.add('btn-outline-secondary');
        }
    }
    
    // Load calendar events
    function loadCalendarEvents() {
        calendarEvents.innerHTML = '<div class="list-group-item"><div class="d-flex w-100 justify-content-between"><h5 class="mb-1">Loading events...</h5></div></div>';
        
        fetch('/calendar')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Calendar API not available');
                }
                return response.json();
            })
            .then(data => {
                calendarEvents.innerHTML = '';
                
                if (data.events && data.events.length > 0) {
                    data.events.forEach(event => {
                        const eventItem = document.createElement('div');
                        eventItem.className = 'list-group-item';
                        
                        eventItem.innerHTML = `
                            <div class="d-flex w-100 justify-content-between">
                                <h5 class="mb-1">${event.event}</h5>
                                <small class="event-time">${event.time}</small>
                            </div>
                        `;
                        
                        calendarEvents.appendChild(eventItem);
                    });
                } else {
                    calendarEvents.innerHTML = '<div class="list-group-item"><div class="d-flex w-100 justify-content-between"><h5 class="mb-1">No events scheduled for today</h5></div></div>';
                }
            })
            .catch(error => {
                console.error('Error loading calendar:', error);
                calendarEvents.innerHTML = `<div class="list-group-item"><div class="d-flex w-100 justify-content-between"><h5 class="mb-1">Error: ${error.message}</h5></div></div>`;
                
                // Show auth UI if needed
                if (error.message === 'Calendar API not available') {
                    document.getElementById('calendar-auth').classList.remove('d-none');
                }
            });
    }
    
    // Search memory
    function searchMemory() {
        const query = memorySearch.value.trim();
        if (query) {
            memoryResults.innerHTML = '<div class="d-flex justify-content-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            
            fetch(`/memory/search?query=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    memoryResults.innerHTML = '';
                    
                    if (data.results && data.results.length > 0) {
                        data.results.forEach(item => {
                            const memoryItem = document.createElement('div');
                            memoryItem.className = 'memory-item';
                            
                            memoryItem.innerHTML = `
                                <div class="memory-key">${item.key}</div>
                                <div class="memory-value">${item.value}</div>
                            `;
                            
                            memoryResults.appendChild(memoryItem);
                        });
                    } else {
                        memoryResults.innerHTML = '<div class="alert alert-info">No results found</div>';
                    }
                })
                .catch(error => {
                    console.error('Error searching memory:', error);
                    memoryResults.innerHTML = '<div class="alert alert-danger">Error searching memory</div>';
                });
        }
    }
    
    // Save to memory
    function saveMemory() {
        const key = memoryKey.value.trim();
        const value = memoryValue.value.trim();
        
        if (key && value) {
            memorySaveBtn.disabled = true;
            memorySaveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
            
            fetch('/memory', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key, value })
            })
            .then(response => response.json())
            .then(data => {
                memoryKey.value = '';
                memoryValue.value = '';
                
                memorySaveBtn.disabled = false;
                memorySaveBtn.innerHTML = 'Save';
                
                if (data.status === 'saved') {
                    alert('Memory saved successfully!');
                } else {
                    alert('Error saving memory');
                }
            })
            .catch(error => {
                console.error('Error saving memory:', error);
                memorySaveBtn.disabled = false;
                memorySaveBtn.innerHTML = 'Save';
                alert('Error saving memory');
            });
        } else {
            alert('Please enter both key and value');
        }
    }
    
    // Check health status
    function checkHealth() {
        fetch('/health')
            .then(response => response.json())
            .then(data => {
                versionInfo.textContent = data.version || '0.1.0';
                
                // Check OpenAI status
                fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: 'test' })
                })
                .then(response => {
                    if (response.ok) {
                        openaiStatus.textContent = 'Connected';
                        openaiStatus.className = 'text-success';
                    } else {
                        openaiStatus.textContent = 'Error';
                        openaiStatus.className = 'text-danger';
                    }
                })
                .catch(() => {
                    openaiStatus.textContent = 'Not configured';
                    openaiStatus.className = 'text-warning';
                });
                
                // Check calendar status
                fetch('/calendar')
                .then(response => {
                    if (response.ok) {
                        calendarStatusInfo.textContent = 'Connected';
                        calendarStatusInfo.className = 'text-success';
                    } else {
                        calendarStatusInfo.textContent = 'Not authorized';
                        calendarStatusInfo.className = 'text-warning';
                    }
                })
                .catch(() => {
                    calendarStatusInfo.textContent = 'Not configured';
                    calendarStatusInfo.className = 'text-warning';
                });
                
                // Check voice status
                fetch('/voice/transcribe', { method: 'POST' })
                .then(response => {
                    if (response.status === 400 || response.status === 422) {
                        voiceStatus.textContent = 'Available';
                        voiceStatus.className = 'text-success';
                    } else if (response.status === 503) {
                        voiceStatus.textContent = 'Disabled';
                        voiceStatus.className = 'text-warning';
                    } else {
                        voiceStatus.textContent = 'Error';
                        voiceStatus.className = 'text-danger';
                    }
                })
                .catch(() => {
                    voiceStatus.textContent = 'Not configured';
                    voiceStatus.className = 'text-warning';
                });
            })
            .catch(error => {
                console.error('Health check error:', error);
            });
    }
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    micButton.addEventListener('click', toggleRecording);
    recordingIndicator.addEventListener('click', stopRecording);
    
    memorySearchBtn.addEventListener('click', searchMemory);
    memorySearch.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchMemory();
        }
    });
    
    memorySaveBtn.addEventListener('click', saveMemory);
    
    // Calendar authentication
    document.getElementById('auth-submit')?.addEventListener('click', function() {
        const authCode = document.getElementById('auth-code').value.trim();
        if (authCode) {
            fetch('/calendar/authorize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: authCode })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Successfully authenticated with Google Calendar!');
                    document.getElementById('calendar-auth').classList.add('d-none');
                    loadCalendarEvents();
                } else {
                    alert('Authentication failed: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Auth error:', error);
                alert('Authentication error');
            });
        } else {
            alert('Please enter the authorization code');
        }
    });
});
