$(document).ready(function() {
    // Handle navigation tabs
    $('.nav-link').on('click', function(e) {
        e.preventDefault();
        
        // Get the target section
        const targetId = $(this).attr('id').replace('-tab', '-section');
        
        // Update active tab
        $('.nav-link').removeClass('active');
        $(this).addClass('active');
        
        // Show target section, hide others
        $('.content-section').removeClass('active');
        $('#' + targetId).addClass('active');
    });
    
    // Handle chat form submission
    $('#chat-form').on('submit', function(e) {
        e.preventDefault();
        
        const input = $('#chat-input');
        const message = input.val().trim();
        
        if (message) {
            // Add user message to chat
            addChatMessage(message, 'user');
            
            // Clear input
            input.val('');
            
            // Send to server and get response
            sendChatMessage(message);
        }
    });
    
    // Handle voice input button
    $('#voice-input-btn').on('click', function() {
        // Check if voice enabled in settings
        if ($('#voice-enabled').is(':checked')) {
            startVoiceRecognition();
        } else {
            showToast('Voice input is not enabled. Please enable it in Settings.', 'warning');
        }
    });
    
    // Handle Home Assistant configuration form
    $('#ha-config-form').on('submit', function(e) {
        e.preventDefault();
        
        const url = $('#ha-url').val().trim();
        const token = $('#ha-token').val().trim();
        
        if (url && token) {
            configureHomeAssistant(url, token);
        } else {
            showToast('Please enter both URL and token.', 'warning');
        }
    });
    
    // Handle AI configuration form
    $('#ai-config-form').on('submit', function(e) {
        e.preventDefault();
        
        const apiKey = $('#openai-api-key').val().trim();
        const voiceEnabled = $('#voice-enabled').is(':checked');
        
        saveAISettings(apiKey, voiceEnabled);
    });
    
    // Handle calendar authorization button
    $('#calendar-auth-btn').on('click', function() {
        const calendarEnabled = $('#calendar-enabled').is(':checked');
        
        if (calendarEnabled) {
            authorizeCalendar();
        } else {
            showToast('Please enable Google Calendar integration first.', 'warning');
        }
    });
    
    // Handle refresh automation suggestions button
    $('#refresh-suggestions-btn').on('click', function() {
        loadAutomationSuggestions();
    });
    
    // Handle refresh active automations button
    $('#refresh-automations-btn').on('click', function() {
        loadActiveAutomations();
    });
    
    // Handle refresh memory button
    $('#refresh-memory-btn').on('click', function() {
        loadMemoryItems();
    });
    
    // Handle add memory button
    $('#add-memory-btn').on('click', function() {
        $('#add-memory-modal').modal('show');
    });
    
    // Handle save memory button
    $('#save-memory-btn').on('click', function() {
        const key = $('#memory-key').val().trim();
        const value = $('#memory-value').val().trim();
        const isPreference = $('#is-preference').is(':checked');
        
        if (key && value) {
            saveMemory(key, value, isPreference);
            $('#add-memory-modal').modal('hide');
        } else {
            showToast('Please enter both key and value.', 'warning');
        }
    });
    
    // Load initial data
    initializeApp();
});

// Helper functions
function addChatMessage(text, sender) {
    const messagesContainer = $('#chat-messages');
    const messageDiv = $('<div></div>').addClass('message').addClass(sender);
    const contentDiv = $('<div></div>').addClass('message-content');
    
    // Add text to message
    contentDiv.append($('<p></p>').text(text));
    
    // Add message to container
    messageDiv.append(contentDiv);
    messagesContainer.append(messageDiv);
    
    // Scroll to bottom
    messagesContainer.scrollTop(messagesContainer[0].scrollHeight);
    
    // Clear any "thinking" indicators if this is a response
    if (sender === 'ai' || sender === 'system') {
        $('.message.thinking').remove();
    }
}

function showThinking() {
    // Add "thinking" indicator
    const messagesContainer = $('#chat-messages');
    const messageDiv = $('<div></div>').addClass('message ai thinking');
    const contentDiv = $('<div></div>').addClass('message-content');
    
    contentDiv.append($('<p></p>').text('Thinking...'));
    
    messageDiv.append(contentDiv);
    messagesContainer.append(messageDiv);
    
    // Scroll to bottom
    messagesContainer.scrollTop(messagesContainer[0].scrollHeight);
}

function sendChatMessage(message) {
    // Show thinking indicator
    showThinking();
    
    // Send to server
    $.ajax({
        url: '/api/ask',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ prompt: message }),
        success: function(response) {
            // Remove thinking indicator and add response
            $('.message.thinking').remove();
            addChatMessage(response.response, 'ai');
        },
        error: function(xhr, status, error) {
            // Remove thinking indicator and add error message
            $('.message.thinking').remove();
            addChatMessage('Sorry, I encountered an error while processing your request.', 'system');
            console.error('Error in chat request:', error);
            showToast('Failed to get response from server.', 'error');
        }
    });
}

function configureHomeAssistant(url, token) {
    $.ajax({
        url: '/api/ha/configure',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ url: url, token: token }),
        success: function(response) {
            showToast('Home Assistant connection configured successfully.', 'success');
            updateConnectionStatus(true);
        },
        error: function(xhr, status, error) {
            console.error('Failed to configure Home Assistant:', error);
            showToast('Failed to configure Home Assistant connection. Please check your URL and token.', 'error');
        }
    });
}

function saveAISettings(apiKey, voiceEnabled) {
    // Save settings to server
    $.ajax({
        url: '/api/settings/ai',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ 
            api_key: apiKey,
            voice_enabled: voiceEnabled
        }),
        success: function(response) {
            showToast('AI settings saved successfully.', 'success');
        },
        error: function(xhr, status, error) {
            console.error('Failed to save AI settings:', error);
            showToast('Failed to save AI settings.', 'error');
        }
    });
}

function authorizeCalendar() {
    // Redirect to authorization URL
    $.ajax({
        url: '/api/calendar/auth-url',
        type: 'GET',
        success: function(response) {
            if (response.auth_url) {
                // Open new window for authorization
                window.open(response.auth_url, '_blank');
                
                // Show instructions
                showToast('Please complete authorization in the opened window.', 'info');
            } else {
                showToast('Failed to get authorization URL.', 'error');
            }
        },
        error: function(xhr, status, error) {
            console.error('Failed to get calendar auth URL:', error);
            showToast('Failed to start calendar authorization.', 'error');
        }
    });
}

function updateConnectionStatus(connected) {
    const indicator = $('.indicator-dot');
    
    if (connected) {
        indicator.addClass('connected');
        indicator.siblings('span').text('Connected to Home Assistant');
    } else {
        indicator.removeClass('connected');
        indicator.siblings('span').text('Not connected to Home Assistant');
    }
}

function loadAutomationSuggestions() {
    $.ajax({
        url: '/api/automations/suggestions',
        type: 'GET',
        success: function(response) {
            const container = $('#automation-suggestions');
            container.empty();
            
            if (response.suggestions && response.suggestions.length > 0) {
                response.suggestions.forEach(function(suggestion) {
                    container.append(createAutomationCard(suggestion, true));
                });
            } else {
                container.append('<p class="text-muted">No automation suggestions available yet. Nexus AI will suggest automations as it learns your patterns.</p>');
            }
        },
        error: function(xhr, status, error) {
            console.error('Failed to load automation suggestions:', error);
            showToast('Failed to load automation suggestions.', 'error');
        }
    });
}

function loadActiveAutomations() {
    $.ajax({
        url: '/api/automations',
        type: 'GET',
        success: function(response) {
            const container = $('#active-automations');
            container.empty();
            
            if (response.automations && response.automations.length > 0) {
                response.automations.forEach(function(automation) {
                    container.append(createAutomationCard(automation, false));
                });
            } else {
                container.append('<p class="text-muted">No active automations found.</p>');
            }
        },
        error: function(xhr, status, error) {
            console.error('Failed to load active automations:', error);
            showToast('Failed to load active automations.', 'error');
        }
    });
}

function createAutomationCard(automation, isSuggestion) {
    const card = $('<div class="automation-card"></div>');
    
    // Title
    card.append(`<div class="title">${automation.name}</div>`);
    
    // Description
    if (automation.description) {
        card.append(`<div class="description">${automation.description}</div>`);
    }
    
    // Confidence bar (for suggestions)
    if (isSuggestion && automation.confidence !== undefined) {
        const confidencePercent = Math.round(automation.confidence * 100);
        card.append(`
            <div class="confidence-bar">
                <div class="confidence-level" style="width: ${confidencePercent}%"></div>
            </div>
            <div class="confidence-text small text-muted">Confidence: ${confidencePercent}%</div>
        `);
    }
    
    // Buttons
    const buttonGroup = $('<div class="btn-group mt-2" role="group"></div>');
    
    if (isSuggestion) {
        // Add "Create" button for suggestions
        buttonGroup.append(`<button class="btn btn-sm btn-primary create-automation-btn" data-id="${automation.id}">Create</button>`);
        buttonGroup.append(`<button class="btn btn-sm btn-outline-danger dismiss-suggestion-btn" data-id="${automation.id}">Dismiss</button>`);
    } else {
        // Add "Enable/Disable" toggle for existing automations
        const toggleBtn = automation.is_enabled ? 
            `<button class="btn btn-sm btn-outline-warning disable-automation-btn" data-id="${automation.id}">Disable</button>` :
            `<button class="btn btn-sm btn-outline-success enable-automation-btn" data-id="${automation.id}">Enable</button>`;
        
        buttonGroup.append(toggleBtn);
        buttonGroup.append(`<button class="btn btn-sm btn-outline-danger delete-automation-btn" data-id="${automation.id}">Delete</button>`);
    }
    
    card.append(buttonGroup);
    
    // Add event handlers
    setTimeout(function() {
        // Create automation button
        card.find('.create-automation-btn').on('click', function() {
            const automationId = $(this).data('id');
            createAutomation(automationId);
        });
        
        // Dismiss suggestion button
        card.find('.dismiss-suggestion-btn').on('click', function() {
            const automationId = $(this).data('id');
            dismissSuggestion(automationId);
        });
        
        // Enable automation button
        card.find('.enable-automation-btn').on('click', function() {
            const automationId = $(this).data('id');
            toggleAutomation(automationId, true);
        });
        
        // Disable automation button
        card.find('.disable-automation-btn').on('click', function() {
            const automationId = $(this).data('id');
            toggleAutomation(automationId, false);
        });
        
        // Delete automation button
        card.find('.delete-automation-btn').on('click', function() {
            const automationId = $(this).data('id');
            deleteAutomation(automationId);
        });
    }, 0);
    
    return card;
}

function createAutomation(suggestionId) {
    $.ajax({
        url: '/api/automations/create',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ suggestion_id: suggestionId }),
        success: function(response) {
            showToast('Automation created successfully.', 'success');
            loadAutomationSuggestions();
            loadActiveAutomations();
        },
        error: function(xhr, status, error) {
            console.error('Failed to create automation:', error);
            showToast('Failed to create automation.', 'error');
        }
    });
}

function dismissSuggestion(suggestionId) {
    $.ajax({
        url: '/api/automations/suggestions/dismiss',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ suggestion_id: suggestionId }),
        success: function(response) {
            showToast('Suggestion dismissed.', 'success');
            loadAutomationSuggestions();
        },
        error: function(xhr, status, error) {
            console.error('Failed to dismiss suggestion:', error);
            showToast('Failed to dismiss suggestion.', 'error');
        }
    });
}

function toggleAutomation(automationId, enable) {
    $.ajax({
        url: '/api/automations/toggle',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ 
            automation_id: automationId,
            enable: enable
        }),
        success: function(response) {
            const action = enable ? 'enabled' : 'disabled';
            showToast(`Automation ${action} successfully.`, 'success');
            loadActiveAutomations();
        },
        error: function(xhr, status, error) {
            console.error('Failed to toggle automation:', error);
            showToast('Failed to update automation.', 'error');
        }
    });
}

function deleteAutomation(automationId) {
    if (confirm('Are you sure you want to delete this automation?')) {
        $.ajax({
            url: '/api/automations/delete',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ automation_id: automationId }),
            success: function(response) {
                showToast('Automation deleted successfully.', 'success');
                loadActiveAutomations();
            },
            error: function(xhr, status, error) {
                console.error('Failed to delete automation:', error);
                showToast('Failed to delete automation.', 'error');
            }
        });
    }
}

function loadMemoryItems() {
    // Load preferences
    $.ajax({
        url: '/api/memory/preferences',
        type: 'GET',
        success: function(response) {
            const container = $('#preferences-list');
            container.empty();
            
            if (response.preferences && Object.keys(response.preferences).length > 0) {
                for (const [key, value] of Object.entries(response.preferences)) {
                    container.append(createMemoryItem(key, value, true));
                }
            } else {
                container.append('<p class="text-muted">No preferences saved yet.</p>');
            }
        },
        error: function(xhr, status, error) {
            console.error('Failed to load preferences:', error);
            showToast('Failed to load preferences.', 'error');
        }
    });
    
    // Load memory items
    $.ajax({
        url: '/api/memory',
        type: 'GET',
        success: function(response) {
            const container = $('#memory-list');
            container.empty();
            
            if (response.memories && response.memories.length > 0) {
                response.memories.forEach(function(memory) {
                    if (!memory.is_preference) {
                        container.append(createMemoryItem(memory.key, memory.value, false));
                    }
                });
            } else {
                container.append('<p class="text-muted">No memory items saved yet.</p>');
            }
        },
        error: function(xhr, status, error) {
            console.error('Failed to load memory items:', error);
            showToast('Failed to load memory items.', 'error');
        }
    });
}

function createMemoryItem(key, value, isPreference) {
    const item = $('<div class="memory-item"></div>');
    
    item.append(`<div class="key">${key}</div>`);
    item.append(`<div class="value">${value}</div>`);
    
    // Add delete button
    const deleteBtn = $(`<button class="btn btn-sm btn-outline-danger mt-2 delete-memory-btn" data-key="${key}">Delete</button>`);
    item.append(deleteBtn);
    
    // Add event handler
    setTimeout(function() {
        deleteBtn.on('click', function() {
            const key = $(this).data('key');
            deleteMemory(key);
        });
    }, 0);
    
    return item;
}

function saveMemory(key, value, isPreference) {
    $.ajax({
        url: '/api/memory',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ 
            key: key,
            value: value,
            is_preference: isPreference
        }),
        success: function(response) {
            showToast('Memory saved successfully.', 'success');
            loadMemoryItems();
            
            // Clear form
            $('#memory-key').val('');
            $('#memory-value').val('');
            $('#is-preference').prop('checked', false);
        },
        error: function(xhr, status, error) {
            console.error('Failed to save memory:', error);
            showToast('Failed to save memory.', 'error');
        }
    });
}

function deleteMemory(key) {
    if (confirm('Are you sure you want to delete this memory item?')) {
        $.ajax({
            url: '/api/memory/delete',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ key: key }),
            success: function(response) {
                showToast('Memory deleted successfully.', 'success');
                loadMemoryItems();
            },
            error: function(xhr, status, error) {
                console.error('Failed to delete memory:', error);
                showToast('Failed to delete memory.', 'error');
            }
        });
    }
}

function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    if ($('#toast-container').length === 0) {
        $('body').append('<div id="toast-container" class="position-fixed bottom-0 end-0 p-3" style="z-index: 11"></div>');
    }
    
    // Create toast
    const toast = $(`
        <div class="toast align-items-center text-white bg-${type}" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `);
    
    // Add to container
    $('#toast-container').append(toast);
    
    // Initialize and show
    const toastInstance = new bootstrap.Toast(toast[0], {
        autohide: true,
        delay: 5000
    });
    toastInstance.show();
}

function startVoiceRecognition() {
    // Check if browser supports speech recognition
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        showToast('Voice recognition is not supported in your browser.', 'warning');
        return;
    }
    
    // Create recognition object
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    // Configure
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    
    // Start recording
    recognition.start();
    
    // Show recording indicator
    $('#voice-input-btn').addClass('btn-danger').removeClass('btn-outline-secondary');
    
    // Handle results
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        $('#chat-input').val(transcript);
    };
    
    // Handle end
    recognition.onend = function() {
        $('#voice-input-btn').removeClass('btn-danger').addClass('btn-outline-secondary');
    };
    
    // Handle errors
    recognition.onerror = function(event) {
        console.error('Voice recognition error:', event.error);
        showToast(`Voice recognition error: ${event.error}`, 'error');
        $('#voice-input-btn').removeClass('btn-danger').addClass('btn-outline-secondary');
    };
}

function loadSettings() {
    // Load Home Assistant settings
    $.ajax({
        url: '/api/settings/ha',
        type: 'GET',
        success: function(response) {
            if (response.url) {
                $('#ha-url').val(response.url);
            }
            // Don't populate token for security reasons
            
            updateConnectionStatus(response.connected || false);
        },
        error: function(xhr, status, error) {
            console.error('Failed to load HA settings:', error);
        }
    });
    
    // Load AI settings
    $.ajax({
        url: '/api/settings/ai',
        type: 'GET',
        success: function(response) {
            // Don't populate API key for security reasons
            $('#voice-enabled').prop('checked', response.voice_enabled || false);
        },
        error: function(xhr, status, error) {
            console.error('Failed to load AI settings:', error);
        }
    });
    
    // Load calendar settings
    $.ajax({
        url: '/api/settings/calendar',
        type: 'GET',
        success: function(response) {
            $('#calendar-enabled').prop('checked', response.enabled || false);
            
            // Update authorization button state
            if (response.authorized) {
                $('#calendar-auth-btn').text('Re-authorize Calendar').removeClass('btn-primary').addClass('btn-outline-primary');
            } else {
                $('#calendar-auth-btn').text('Authorize Calendar').addClass('btn-primary').removeClass('btn-outline-primary');
            }
        },
        error: function(xhr, status, error) {
            console.error('Failed to load calendar settings:', error);
        }
    });
}

// Initialize WebSocket connection
function initWebSocket() {
    // Check if browser supports WebSocket
    if (!('WebSocket' in window)) {
        console.error('WebSockets not supported');
        return;
    }
    
    // Create WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = protocol + '//' + window.location.host + '/ws';
    const socket = new WebSocket(wsUrl);
    
    socket.onopen = function() {
        console.log('WebSocket connected');
    };
    
    socket.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            
            // Handle different message types
            if (data.type === 'new_suggestion') {
                showToast('New automation suggestion available.', 'info');
                loadAutomationSuggestions();
            } else if (data.type === 'ha_state_change') {
                // Handle state change
                console.log('State change:', data.entity_id, data.new_state);
            } else if (data.type === 'connection_status') {
                updateConnectionStatus(data.connected);
            }
        } catch (e) {
            console.error('Error parsing WebSocket message:', e);
        }
    };
    
    socket.onclose = function() {
        console.log('WebSocket disconnected');
        // Try to reconnect after a delay
        setTimeout(initWebSocket, 5000);
    };
    
    socket.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
}

function initializeApp() {
    // Load all data
    loadSettings();
    loadAutomationSuggestions();
    loadActiveAutomations();
    loadMemoryItems();
    
    // Initialize WebSocket
    initWebSocket();
}
