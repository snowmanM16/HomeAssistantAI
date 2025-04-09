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
        // TODO: Implement voice recognition
        alert('Voice input is not yet implemented.');
    });
    
    // Handle Home Assistant configuration form
    $('#ha-config-form').on('submit', function(e) {
        e.preventDefault();
        
        const url = $('#ha-url').val().trim();
        const token = $('#ha-token').val().trim();
        
        if (url && token) {
            configureHomeAssistant(url, token);
        } else {
            alert('Please enter both URL and token.');
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
            alert('Please enable Google Calendar integration first.');
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
}

function sendChatMessage(message) {
    // Show typing indicator
    addChatMessage('...', 'ai');
    
    // Send to server
    $.ajax({
        url: '/api/ask',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ prompt: message }),
        success: function(response) {
            // Remove typing indicator and add response
            $('#chat-messages .message.ai:last-child').remove();
            addChatMessage(response.response, 'ai');
        },
        error: function() {
            // Remove typing indicator and add error message
            $('#chat-messages .message.ai:last-child').remove();
            addChatMessage('Sorry, I encountered an error while processing your request.', 'system');
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
            alert('Home Assistant connection configured successfully.');
            updateConnectionStatus(true);
        },
        error: function() {
            alert('Failed to configure Home Assistant connection. Please check your URL and token.');
        }
    });
}

function saveAISettings(apiKey, voiceEnabled) {
    // TODO: Implement saving AI settings
    alert('AI settings saved successfully.');
}

function authorizeCalendar() {
    // TODO: Implement calendar authorization
    alert('Google Calendar authorization is not yet implemented.');
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
    // TODO: Load automation suggestions from server
}

function loadActiveAutomations() {
    // TODO: Load active automations from server
}

function loadMemoryItems() {
    // TODO: Load memory items from server
}

function initializeApp() {
    // Check Home Assistant connection status
    $.ajax({
        url: '/api/ha/status',
        type: 'GET',
        success: function(response) {
            updateConnectionStatus(response.connected);
        },
        error: function() {
            updateConnectionStatus(false);
        }
    });
    
    // Load automations and memory
    loadAutomationSuggestions();
    loadActiveAutomations();
    loadMemoryItems();
}

// Initialize WebSocket connection
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = protocol + '//' + window.location.host + '/ws';
    const socket = new WebSocket(wsUrl);
    
    socket.onopen = function() {
        console.log('WebSocket connected');
    };
    
    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);
        
        // Handle different message types
        if (data.type === 'ha_state_change') {
            // Update UI based on state change
        } else if (data.type === 'new_automation_suggestion') {
            // Show new automation suggestion
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

// Initialize WebSocket
initWebSocket();
