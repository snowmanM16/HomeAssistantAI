// Modern UI JavaScript for Nexus AI

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    const menuToggle = document.getElementById('menuToggle');
    const navLinks = document.querySelectorAll('.nav-link');
    const pageTitle = document.getElementById('pageTitle');
    const sections = document.querySelectorAll('.section-content');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const micBtn = document.getElementById('micBtn');
    const chatMessages = document.getElementById('chatMessages');
    const memorySearchBtn = document.getElementById('memorySearchBtn');
    const memorySearchInput = document.getElementById('memorySearchInput');
    const memoryResults = document.getElementById('memoryResults');
    const memorySaveBtn = document.getElementById('memorySaveBtn');
    const memoryKey = document.getElementById('memoryKey');
    const memoryValue = document.getElementById('memoryValue');
    const eventList = document.getElementById('eventList');
    const refreshBtn = document.getElementById('refreshBtn');
    
    // Home Assistant configuration elements
    const haConfigForm = document.getElementById('haConfigForm');
    const haUrl = document.getElementById('haUrl');
    const haToken = document.getElementById('haToken');
    const haStatus = document.getElementById('haStatus');
    
    // Automation elements
    const automationList = document.getElementById('automationList');
    const automationSuggestions = document.getElementById('automationSuggestions');
    const refreshSuggestionsBtn = document.getElementById('refreshSuggestionsBtn');
    const automationName = document.getElementById('automationName');
    const automationDescription = document.getElementById('automationDescription');
    const createFromDescriptionBtn = document.getElementById('createFromDescriptionBtn');

    // Variables
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;

    // Initialize UI
    checkHealth();
    
    // Sidebar toggle functionality
    menuToggle.addEventListener('click', function() {
        sidebar.classList.toggle('active');
        overlay.classList.toggle('active');
    });

    overlay.addEventListener('click', function() {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
    });

    // Section navigation
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all links
            navLinks.forEach(l => l.classList.remove('active'));
            
            // Add active class to clicked link
            this.classList.add('active');
            
            const sectionId = this.getAttribute('data-section');
            pageTitle.textContent = this.textContent.trim();
            
            // Hide all sections
            sections.forEach(section => section.classList.remove('active'));
            
            // Show selected section
            const selectedSection = document.getElementById(sectionId + 'Section');
            if (selectedSection) {
                selectedSection.classList.add('active');
                
                // Load section-specific data
                if (sectionId === 'calendar') {
                    loadCalendarEvents();
                } else if (sectionId === 'automations') {
                    loadAutomations();
                    loadAutomationSuggestions();
                } else if (sectionId === 'settings') {
                    checkHomeAssistantStatus();
                }
            }
            
            // Close sidebar on mobile
            if (window.innerWidth < 768) {
                sidebar.classList.remove('active');
                overlay.classList.remove('active');
            }
        });
    });

    // Input behavior and sending messages
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Auto-resize textarea
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }
    
    if (micBtn) {
        micBtn.addEventListener('click', toggleRecording);
    }

    // Memory functions
    if (memorySearchBtn) {
        memorySearchBtn.addEventListener('click', searchMemory);
    }
    
    if (memorySaveBtn) {
        memorySaveBtn.addEventListener('click', saveMemory);
    }

    // Refresh button
    refreshBtn.addEventListener('click', function() {
        const activeSection = document.querySelector('.section-content.active');
        const sectionId = activeSection.id;
        
        if (sectionId === 'chatSection') {
            // Just refresh health check for chat
            checkHealth();
        } else if (sectionId === 'calendarSection') {
            loadCalendarEvents();
        } else if (sectionId === 'memorySection') {
            // Clear search results
            memoryResults.innerHTML = '';
            memorySearchInput.value = '';
        } else if (sectionId === 'automationsSection') {
            loadAutomations();
            loadAutomationSuggestions();
        } else if (sectionId === 'settingsSection') {
            checkHealth();
            checkHomeAssistantStatus();
        }
    });

    // Home Assistant Configuration
    if (haConfigForm) {
        haConfigForm.addEventListener('submit', function(e) {
            e.preventDefault();
            configureHomeAssistant();
        });
    }
    
    // Automation functions
    if (refreshSuggestionsBtn) {
        refreshSuggestionsBtn.addEventListener('click', loadAutomationSuggestions);
    }
    
    if (createFromDescriptionBtn) {
        createFromDescriptionBtn.addEventListener('click', createAutomationFromDescription);
    }

    // Functions
    function sendMessage() {
        const message = messageInput.value.trim();
        if (message) {
            // Add user message to chat
            addMessage(message, 'user');
            
            // Clear input field
            messageInput.value = '';
            messageInput.style.height = 'auto';
            
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

    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Format the text with basic markdown-like formatting
        text = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
            
        contentDiv.innerHTML = text;
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        timeDiv.textContent = `Today at ${timeString}`;
        
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);
        
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTypingIndicator() {
        const indicatorDiv = document.createElement('div');
        indicatorDiv.className = 'message system-message typing';
        indicatorDiv.id = 'typingIndicator';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
        
        indicatorDiv.appendChild(contentDiv);
        chatMessages.appendChild(indicatorDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    function toggleRecording() {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    }

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
                    const processingId = 'processing-' + Date.now();
                    const processingDiv = document.createElement('div');
                    processingDiv.className = 'message system-message';
                    processingDiv.id = processingId;
                    
                    const contentDiv = document.createElement('div');
                    contentDiv.className = 'message-content';
                    contentDiv.innerHTML = 'Processing your voice...';
                    
                    processingDiv.appendChild(contentDiv);
                    chatMessages.appendChild(processingDiv);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                    
                    // Send to the API for transcription
                    fetch('/voice/transcribe', {
                        method: 'POST',
                        body: audioBlob
                    })
                    .then(response => response.json())
                    .then(data => {
                        // Remove the processing message
                        document.getElementById(processingId).remove();
                        
                        if (data.text && data.text.trim()) {
                            // Add the transcribed text as a user message
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
                        document.getElementById(processingId).remove();
                        addMessage('Sorry, there was an error processing the audio.', 'system');
                    });
                    
                    stream.getTracks().forEach(track => track.stop());
                });
                
                mediaRecorder.start();
                isRecording = true;
                micBtn.classList.add('recording');
                micBtn.innerHTML = '<i class="bi bi-mic-mute"></i>';
            })
            .catch(error => {
                console.error('Error accessing microphone:', error);
                addMessage('Sorry, I couldn\'t access your microphone.', 'system');
            });
    }

    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            micBtn.classList.remove('recording');
            micBtn.innerHTML = '<i class="bi bi-mic"></i>';
        }
    }

    function loadCalendarEvents() {
        if (!eventList) return;
        
        eventList.innerHTML = `
            <li class="event-item">
                <div class="event-time">Loading...</div>
                <div class="event-details">
                    <div class="event-title">Fetching your events</div>
                </div>
            </li>
        `;
        
        fetch('/calendar')
            .then(response => response.json())
            .then(data => {
                eventList.innerHTML = '';
                
                if (data.events && data.events.length > 0) {
                    data.events.forEach(event => {
                        const eventItem = document.createElement('li');
                        eventItem.className = 'event-item';
                        
                        const eventTime = document.createElement('div');
                        eventTime.className = 'event-time';
                        eventTime.textContent = event.time || 'No time specified';
                        
                        const eventDetails = document.createElement('div');
                        eventDetails.className = 'event-details';
                        
                        const eventTitle = document.createElement('div');
                        eventTitle.className = 'event-title';
                        eventTitle.textContent = event.summary || 'Untitled Event';
                        
                        const eventLocation = document.createElement('div');
                        eventLocation.className = 'event-location';
                        eventLocation.textContent = event.location || '';
                        
                        eventDetails.appendChild(eventTitle);
                        if (event.location) {
                            eventDetails.appendChild(eventLocation);
                        }
                        
                        eventItem.appendChild(eventTime);
                        eventItem.appendChild(eventDetails);
                        
                        eventList.appendChild(eventItem);
                    });
                } else {
                    eventList.innerHTML = `
                        <li class="event-item">
                            <div class="event-details">
                                <div class="event-title">No events found for today</div>
                            </div>
                        </li>
                    `;
                }
            })
            .catch(error => {
                console.error('Error loading calendar:', error);
                eventList.innerHTML = `
                    <li class="event-item">
                        <div class="event-details">
                            <div class="event-title">Error loading calendar events</div>
                            <div class="event-location">${error.message}</div>
                        </div>
                    </li>
                `;
                
                // Show auth UI if needed
                const calendarAuthCard = document.getElementById('calendarAuthCard');
                if (calendarAuthCard) {
                    calendarAuthCard.style.display = 'block';
                }
            });
    }

    function searchMemory() {
        const query = memorySearchInput.value.trim();
        if (!query) return;
        
        memoryResults.innerHTML = `
            <div class="memory-item">
                <div class="memory-key">Searching...</div>
                <div class="memory-value">Please wait while we search for "${query}"</div>
            </div>
        `;
        
        fetch(`/memory/search?query=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                memoryResults.innerHTML = '';
                
                if (data.results && data.results.length > 0) {
                    data.results.forEach(result => {
                        const memoryItem = document.createElement('div');
                        memoryItem.className = 'memory-item';
                        
                        const memoryKey = document.createElement('div');
                        memoryKey.className = 'memory-key';
                        memoryKey.textContent = result.key;
                        
                        const memoryValue = document.createElement('div');
                        memoryValue.className = 'memory-value';
                        memoryValue.textContent = result.value;
                        
                        const memoryActions = document.createElement('div');
                        memoryActions.className = 'memory-actions';
                        
                        const editBtn = document.createElement('button');
                        editBtn.className = 'btn btn-secondary btn-sm';
                        editBtn.textContent = 'Edit';
                        editBtn.addEventListener('click', () => {
                            memoryKey.value = result.key;
                            memoryValue.value = result.value;
                        });
                        
                        const deleteBtn = document.createElement('button');
                        deleteBtn.className = 'btn btn-danger btn-sm';
                        deleteBtn.textContent = 'Delete';
                        deleteBtn.addEventListener('click', () => {
                            if (confirm(`Delete memory item "${result.key}"?`)) {
                                // Implement memory deletion
                                console.log('Delete memory:', result.key);
                            }
                        });
                        
                        memoryActions.appendChild(editBtn);
                        memoryActions.appendChild(deleteBtn);
                        
                        memoryItem.appendChild(memoryKey);
                        memoryItem.appendChild(memoryValue);
                        memoryItem.appendChild(memoryActions);
                        
                        memoryResults.appendChild(memoryItem);
                    });
                } else {
                    memoryResults.innerHTML = `
                        <div class="memory-item">
                            <div class="memory-key">No results</div>
                            <div class="memory-value">No memories found for "${query}"</div>
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error searching memory:', error);
                memoryResults.innerHTML = `
                    <div class="memory-item">
                        <div class="memory-key">Error</div>
                        <div class="memory-value">Failed to search memory: ${error.message}</div>
                    </div>
                `;
            });
    }

    function saveMemory() {
        const key = memoryKey.value.trim();
        const value = memoryValue.value.trim();
        
        if (!key || !value) {
            alert('Please provide both a key and value for the memory');
            return;
        }
        
        const originalButtonText = memorySaveBtn.innerHTML;
        memorySaveBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving...';
        memorySaveBtn.disabled = true;
        
        fetch('/memory', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                key: key,
                value: value
            })
        })
        .then(response => response.json())
        .then(data => {
            memorySaveBtn.innerHTML = originalButtonText;
            memorySaveBtn.disabled = false;
            
            if (data.status === 'saved') {
                memoryKey.value = '';
                memoryValue.value = '';
                
                const successElement = document.createElement('div');
                successElement.className = 'alert alert-success';
                successElement.textContent = 'Memory saved successfully!';
                
                memorySaveBtn.parentNode.appendChild(successElement);
                
                // Remove success message after 3 seconds
                setTimeout(() => {
                    successElement.remove();
                }, 3000);
            } else {
                alert('Error saving memory: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error saving memory:', error);
            memorySaveBtn.innerHTML = originalButtonText;
            memorySaveBtn.disabled = false;
            alert('Error saving memory: ' + error.message);
        });
    }

    function checkHealth() {
        fetch('/health')
            .then(response => response.json())
            .then(data => {
                const openaiStatus = document.getElementById('openaiStatus');
                const calendarStatus = document.getElementById('calendarStatus');
                const voiceToggle = document.getElementById('voiceToggle');
                
                if (openaiStatus) {
                    // Check OpenAI connection
                    fetch('/ask', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ prompt: 'status check' })
                    })
                    .then(response => {
                        if (response.ok) {
                            openaiStatus.innerHTML = '<span class="status-dot connected"></span><span>Connected</span>';
                        } else {
                            openaiStatus.innerHTML = '<span class="status-dot error"></span><span>Error</span>';
                        }
                    })
                    .catch(() => {
                        openaiStatus.innerHTML = '<span class="status-dot disconnected"></span><span>Not configured</span>';
                    });
                }
                
                if (calendarStatus) {
                    // Check Calendar connection
                    fetch('/calendar')
                    .then(response => {
                        if (response.ok) {
                            calendarStatus.innerHTML = '<span class="status-dot connected"></span><span>Connected</span>';
                        } else {
                            calendarStatus.innerHTML = '<span class="status-dot pending"></span><span>Not authorized</span>';
                        }
                    })
                    .catch(() => {
                        calendarStatus.innerHTML = '<span class="status-dot disconnected"></span><span>Not configured</span>';
                    });
                }
                
                // Check voice processing status
                if (voiceToggle) {
                    fetch('/voice/transcribe', { method: 'POST' })
                    .then(response => {
                        voiceToggle.checked = response.ok;
                    })
                    .catch(() => {
                        voiceToggle.checked = false;
                    });
                }
            })
            .catch(error => {
                console.error('Health check error:', error);
            });
    }

    // Home Assistant configuration and status check
    function configureHomeAssistant() {
        const url = haUrl.value.trim();
        const token = haToken.value.trim();
        
        if (!url) {
            alert('Please enter the Home Assistant URL');
            return;
        }
        
        if (!token) {
            alert('Please enter a long-lived access token');
            return;
        }
        
        const submitBtn = haConfigForm.querySelector('button[type="submit"]');
        const originalButtonText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Connecting...';
        submitBtn.disabled = true;
        
        fetch('/ha/configure', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                token: token
            })
        })
        .then(response => response.json())
        .then(data => {
            submitBtn.innerHTML = originalButtonText;
            submitBtn.disabled = false;
            
            if (data.status === 'configured' && data.connection.connected) {
                alert('Home Assistant connection configured successfully!');
                haToken.value = ''; // Clear token for security
                checkHomeAssistantStatus();
            } else {
                alert('Error configuring Home Assistant: ' + (data.connection.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error configuring Home Assistant:', error);
            submitBtn.innerHTML = originalButtonText;
            submitBtn.disabled = false;
            alert('Error configuring Home Assistant: ' + error.message);
        });
    }
    
    function checkHomeAssistantStatus() {
        if (!haStatus) return;
        
        haStatus.innerHTML = '<span class="status-dot pending"></span><span>Checking...</span>';
        
        fetch('/ha/status')
            .then(response => response.json())
            .then(data => {
                if (data.configured && data.connection.connected) {
                    haStatus.innerHTML = `<span class="status-dot connected"></span><span>Connected to ${data.connection.location_name || 'Home Assistant'} (${data.connection.version || 'unknown'})</span>`;
                } else if (data.configured) {
                    haStatus.innerHTML = `<span class="status-dot error"></span><span>Connection error: ${data.connection.error || 'Unknown error'}</span>`;
                } else {
                    haStatus.innerHTML = '<span class="status-dot disconnected"></span><span>Not configured</span>';
                }
            })
            .catch(error => {
                console.error('Error checking Home Assistant status:', error);
                haStatus.innerHTML = '<span class="status-dot error"></span><span>Error checking status</span>';
            });
    }
    
    // Automation functions
    function loadAutomations() {
        if (!automationList) return;
        
        automationList.innerHTML = '<div class="loading-spinner"></div>';
        
        fetch('/automations')
            .then(response => response.json())
            .then(data => {
                automationList.innerHTML = '';
                
                if (data.automations && data.automations.length > 0) {
                    data.automations.forEach(automation => {
                        const automationItem = document.createElement('div');
                        automationItem.className = 'automation-item';
                        
                        const isActive = automation.state === 'on';
                        automationItem.classList.add(isActive ? 'active' : 'inactive');
                        
                        automationItem.innerHTML = `
                            <div class="automation-header">
                                <span class="automation-name">${automation.name}</span>
                                <span class="automation-status ${isActive ? 'enabled' : 'disabled'}">${isActive ? 'Enabled' : 'Disabled'}</span>
                            </div>
                            <div class="automation-controls">
                                <button class="btn btn-sm ${isActive ? 'btn-warning' : 'btn-success'}" data-entity="${automation.entity_id}" data-action="${isActive ? 'disable' : 'enable'}">
                                    ${isActive ? '<i class="bi bi-pause-fill"></i> Disable' : '<i class="bi bi-play-fill"></i> Enable'}
                                </button>
                                <button class="btn btn-sm btn-primary" data-entity="${automation.entity_id}" data-action="trigger">
                                    <i class="bi bi-lightning"></i> Trigger
                                </button>
                            </div>
                        `;
                        
                        automationList.appendChild(automationItem);
                        
                        // Add event listeners
                        const toggleBtn = automationItem.querySelector(`button[data-action="${isActive ? 'disable' : 'enable'}"]`);
                        toggleBtn.addEventListener('click', () => toggleAutomation(automation.entity_id, !isActive));
                        
                        const triggerBtn = automationItem.querySelector('button[data-action="trigger"]');
                        triggerBtn.addEventListener('click', () => triggerAutomation(automation.entity_id));
                    });
                } else {
                    automationList.innerHTML = '<div class="no-items">No automations found</div>';
                }
            })
            .catch(error => {
                console.error('Error loading automations:', error);
                automationList.innerHTML = `<div class="error-message">Error loading automations: ${error.message}</div>`;
            });
    }
    
    function loadAutomationSuggestions() {
        if (!automationSuggestions) return;
        
        automationSuggestions.innerHTML = '<div class="loading-spinner"></div>';
        
        fetch('/automations/suggestions')
            .then(response => response.json())
            .then(data => {
                automationSuggestions.innerHTML = '';
                
                if (data.suggestions && data.suggestions.length > 0) {
                    data.suggestions.forEach(suggestion => {
                        const suggestionItem = document.createElement('div');
                        suggestionItem.className = 'suggestion-item';
                        
                        suggestionItem.innerHTML = `
                            <div class="suggestion-details">
                                <div class="suggestion-title">${suggestion.name || suggestion.description}</div>
                                <div class="suggestion-description">${suggestion.description}</div>
                                <div class="suggestion-confidence">Confidence: ${Math.round(suggestion.confidence * 100)}%</div>
                            </div>
                            <div class="suggestion-actions">
                                <button class="btn btn-primary btn-sm" data-suggestion="${encodeURIComponent(JSON.stringify(suggestion))}">Apply</button>
                            </div>
                        `;
                        
                        automationSuggestions.appendChild(suggestionItem);
                        
                        // Add event listener for apply button
                        const applyBtn = suggestionItem.querySelector('button');
                        applyBtn.addEventListener('click', () => {
                            const suggestionData = JSON.parse(decodeURIComponent(applyBtn.dataset.suggestion));
                            applyAutomationSuggestion(suggestionData);
                        });
                    });
                } else {
                    automationSuggestions.innerHTML = `
                        <div class="suggestion-item">
                            <div class="suggestion-details">
                                <div class="suggestion-title">No suggestions available</div>
                                <div class="suggestion-description">Nexus AI hasn't detected any automation patterns yet. Keep using your smart home and check back later.</div>
                            </div>
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error loading automation suggestions:', error);
                automationSuggestions.innerHTML = `
                    <div class="suggestion-item">
                        <div class="suggestion-details">
                            <div class="suggestion-title">Error loading suggestions</div>
                            <div class="suggestion-description">${error.message}</div>
                        </div>
                    </div>
                `;
            });
    }
    
    function toggleAutomation(entityId, enable) {
        fetch(`/automations/toggle/${entityId}?enable=${enable}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload automations to show updated state
                loadAutomations();
            } else {
                alert(`Error toggling automation: ${data.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            console.error('Error toggling automation:', error);
            alert(`Error toggling automation: ${error.message}`);
        });
    }
    
    function triggerAutomation(entityId) {
        fetch(`/automations/trigger/${entityId}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(`Automation "${entityId}" triggered successfully`);
            } else {
                alert(`Error triggering automation: ${data.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            console.error('Error triggering automation:', error);
            alert(`Error triggering automation: ${error.message}`);
        });
    }
    
    function applyAutomationSuggestion(suggestion) {
        // Check if suggestion has the necessary data
        if (!suggestion.name || !suggestion.triggers || !suggestion.actions) {
            alert('Invalid automation suggestion data');
            return;
        }
        
        const requestData = {
            name: suggestion.name,
            triggers: suggestion.triggers,
            actions: suggestion.actions
        };
        
        if (suggestion.conditions) {
            requestData.conditions = suggestion.conditions;
        }
        
        fetch('/automations/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(`Automation "${suggestion.name}" created successfully!`);
                loadAutomations();
            } else {
                alert(`Error creating automation: ${data.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            console.error('Error creating automation:', error);
            alert(`Error creating automation: ${error.message}`);
        });
    }
    
    function createAutomationFromDescription() {
        const name = automationName.value.trim();
        const description = automationDescription.value.trim();
        
        if (!name || !description) {
            alert('Please provide both a name and description for the automation');
            return;
        }
        
        const createBtn = createFromDescriptionBtn;
        const originalText = createBtn.innerHTML;
        createBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Creating...';
        createBtn.disabled = true;
        
        // First, ask the AI to generate an automation based on the description
        fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt: `Please create a Home Assistant automation with this description: "${description}". Respond with only the JSON for the automation, including triggers, conditions (if needed), and actions. Make it compatible with Home Assistant's automation API.`
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.response) {
                // Try to extract JSON from the AI response
                try {
                    // Look for JSON block in the response
                    let jsonStr = data.response;
                    const jsonMatch = jsonStr.match(/```json\n([\s\S]*?)\n```/) || jsonStr.match(/```([\s\S]*?)```/);
                    
                    if (jsonMatch) {
                        jsonStr = jsonMatch[1];
                    }
                    
                    const automation = JSON.parse(jsonStr);
                    
                    // Now create the automation
                    return fetch('/automations/create', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            name: name,
                            triggers: automation.trigger,
                            conditions: automation.condition,
                            actions: automation.action
                        })
                    });
                } catch (error) {
                    throw new Error(`Failed to parse automation: ${error.message}`);
                }
            } else {
                throw new Error('AI did not return a valid response');
            }
        })
        .then(response => response.json())
        .then(data => {
            createBtn.innerHTML = originalText;
            createBtn.disabled = false;
            
            if (data.success) {
                alert(`Automation "${name}" created successfully!`);
                automationName.value = '';
                automationDescription.value = '';
                loadAutomations();
            } else {
                alert(`Error creating automation: ${data.error || 'Unknown error'}`);
            }
        })
        .catch(error => {
            console.error('Error creating automation from description:', error);
            createBtn.innerHTML = originalText;
            createBtn.disabled = false;
            alert(`Error creating automation: ${error.message}`);
        });
    }
});
