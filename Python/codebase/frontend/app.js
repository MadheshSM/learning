/**
 * ACC Dashboard - Multi-Agent Analytics Frontend
 */

// Auth guard - check URL token param first, then localStorage
(function() {
    // Clean up stale flags from localStorage
    localStorage.removeItem('is_iframe');
    localStorage.removeItem('acc_user_id');

    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get('token');
    if (urlToken) {
        localStorage.setItem('auth_token', urlToken);
        // Clean token from URL without reload
        window.history.replaceState({}, '', window.location.pathname);
    }
    if (!localStorage.getItem('auth_token')) {
        window.location.href = '/login';
    }
    // Hide logout button only when actually inside an iframe
    if (window.self !== window.top) {
        document.addEventListener('DOMContentLoaded', () => {
            const logoutBtn = document.getElementById('logout-btn');
            if (logoutBtn) logoutBtn.style.display = 'none';
        });
    }
})();

// Logout function
function logout() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('auth_user');
    window.location.href = '/login';
}

// Global state
const state = {
    grid: null,
    charts: {},
    currentProject: null,
    isLoading: false,
    timelineExpanded: false,
    sourcesExpanded: false,
    dataSource: 'krion6d',           // 'acc' or 'krion6d'
    module: 'design',           // Krion6d API module
    accConnected: false,
    widgetConfigs: {},           // widgetId → chart config (for CSV export)
    lastQuery: '',
    lastSummary: '',
    // Layout tracking for training
    layoutTracking: {
        chartConfigs: [],      // Original chart configs from API
        renderedLayout: [],    // Layout as initially rendered
        userLayout: [],        // Layout after user modifications
        hasUserChanges: false
    }
};

// DOM Elements
const elements = {
    queryInput: document.getElementById('query-input'),
    queryBtn: document.getElementById('query-btn'),
    queryBtnText: document.getElementById('query-btn-text'),
    queryBtnSpinner: document.getElementById('query-btn-spinner'),
    clearInputBtn: document.getElementById('clear-input-btn'),
    projectSelector: document.getElementById('project-selector'),
    reloadBtn: document.getElementById('reload-btn'),
    exportAllTrigger: document.getElementById('export-all-trigger'),
    exportFormatSelector: document.getElementById('export-format-selector'),
    responseSection: document.getElementById('response-section'),
    routingInfo: document.getElementById('routing-info'),
    detectedIntent: document.getElementById('detected-intent'),
    selectedAgents: document.getElementById('selected-agents'),
    routingReasoning: document.getElementById('routing-reasoning'),
    agentResponseSection: document.getElementById('agent-response-section'),
    messageContent: document.getElementById('message-content'),
    dashboardGrid: document.getElementById('dashboard-grid'),
    emptyState: document.getElementById('empty-state'),
    errorToast: document.getElementById('error-toast'),
    errorMessage: document.getElementById('error-message'),
    statusIndicator: document.getElementById('status-indicator'),
    processingStatus: document.getElementById('processing-status'),
    processingMessage: document.getElementById('processing-message'),
    processingDetail: document.getElementById('processing-detail'),
    liveLog: document.getElementById('live-log'),
    interactionTimeline: document.getElementById('interaction-timeline'),
    timelineSummary: document.getElementById('timeline-summary'),
    timelineContainer: document.getElementById('timeline-container'),
    toggleTimeline: document.getElementById('toggle-timeline'),
    chatEmptyState: document.getElementById('chat-empty-state'),
    chatMessages: document.getElementById('chat-messages'),
    viewPromptsBtn: document.getElementById('view-prompts-btn'),
    promptsDropdown: document.getElementById('prompts-dropdown'),
    promptsChevron: document.getElementById('prompts-chevron'),
    dataSources: document.getElementById('data-sources'),
    sourcesSummary: document.getElementById('sources-summary'),
    sourcesContainer: document.getElementById('sources-container'),
    toggleSources: document.getElementById('toggle-sources'),
    dataSourceToggle: document.getElementById('data-source-toggle'),
    sourceAcc: document.getElementById('source-acc'),
    sourceKrion6d: document.getElementById('source-krion6d'),
    sourceErp: document.getElementById('source-erp'),
    moduleSelector: document.getElementById('module-selector'),
    accStatusIndicator: document.getElementById('acc-status-indicator'),
    accStatusText: document.getElementById('acc-status-text'),
    accLoginModal: document.getElementById('acc-login-modal'),
    accModalNotConnected: document.getElementById('acc-modal-not-connected'),
    accModalConnecting: document.getElementById('acc-modal-connecting'),
    accModalConnected: document.getElementById('acc-modal-connected'),
    accModalUserInfo: document.getElementById('acc-modal-user-info'),
};

// Interaction type configuration
const interactionConfig = {
    query_received: { color: 'blue', label: 'Query Received' },
    routing_start: { color: 'purple', label: 'Analyzing Intent' },
    routing_decision: { color: 'green', label: 'Agent Selected' },
    agent_start: { color: 'blue', label: 'Agent Started' },
    tool_call: { color: 'amber', label: 'Tool Call' },
    tool_result: { color: 'teal', label: 'Tool Result' },
    agent_thinking: { color: 'gray', label: 'Processing' },
    agent_response: { color: 'green', label: 'Agent Response' },
    synthesis_start: { color: 'purple', label: 'Synthesizing' },
    synthesis_complete: { color: 'green', label: 'Complete' },
    error: { color: 'red', label: 'Error' }
};

// Agent display names and colors
const agentConfig = {
    data_analyst: { name: 'Data Analyst', color: 'blue' },
    safety: { name: 'Safety', color: 'red' },
    schedule: { name: 'Schedule', color: 'green' },
    cost: { name: 'Cost', color: 'amber' }
};

// Initialize Gridstack
function initGrid() {
    state.grid = GridStack.init({
        column: 12,
        cellHeight: 60,
        margin: 8,
        float: true, // Allow floating for more flexible layouts
        resizable: { handles: 'e,se,s,sw,w' },
        animate: true,
        disableOneColumnMode: true
    });

    // Log layout changes when user resizes/moves widgets
    state.grid.on('change', (event, items) => {
        logLayoutChange(items);
    });
}

function logLayoutChange(items) {
    const layout = items.map(item => {
        const el = item.el;
        const title = el.querySelector('h3 span')?.textContent || 'Unknown';
        const chartType = el.querySelector('canvas')?.id ? 'chart' :
                         el.querySelector('.text-3xl') ? 'kpi' :
                         el.querySelector('table') ? 'table' : 'unknown';
        return {
            title: title,
            type: chartType,
            x: item.x,
            y: item.y,
            w: item.w,
            h: item.h
        };
    });

    // Store user layout
    state.layoutTracking.userLayout = layout;
    state.layoutTracking.hasUserChanges = true;

    // Save to localStorage
    saveLayoutTrackingData();

    console.log('=== USER LAYOUT CHANGE ===');
    console.log('Layout:', JSON.stringify(layout, null, 2));
    console.log('==========================');
}

function captureRenderedLayout() {
    // Capture layout after initial render
    setTimeout(() => {
        const items = state.grid.getGridItems();
        const layout = items.map(el => {
            const node = el.gridstackNode;
            const title = el.querySelector('h3 span')?.textContent || 'Unknown';
            const chartType = el.querySelector('canvas')?.id ? 'chart' :
                             el.querySelector('.text-3xl') ? 'kpi' :
                             el.querySelector('table') ? 'table' : 'unknown';
            return {
                title: title,
                type: chartType,
                x: node.x,
                y: node.y,
                w: node.w,
                h: node.h
            };
        });

        state.layoutTracking.renderedLayout = layout;
        state.layoutTracking.userLayout = JSON.parse(JSON.stringify(layout)); // Clone
        state.layoutTracking.hasUserChanges = false;

        // Save initial state
        saveLayoutTrackingData();

        console.log('=== INITIAL RENDERED LAYOUT ===');
        console.log('Layout:', JSON.stringify(layout, null, 2));
        console.log('================================');
    }, 500);
}

function saveLayoutTrackingData() {
    const trackingData = {
        timestamp: new Date().toISOString(),
        chartConfigs: state.layoutTracking.chartConfigs,
        renderedLayout: state.layoutTracking.renderedLayout,
        userLayout: state.layoutTracking.userLayout,
        hasUserChanges: state.layoutTracking.hasUserChanges
    };

    // Save to localStorage
    const history = JSON.parse(localStorage.getItem('layoutTrainingData') || '[]');

    // Update last entry if no user changes yet, otherwise add new
    if (history.length > 0 && !history[history.length - 1].hasUserChanges) {
        history[history.length - 1] = trackingData;
    } else if (state.layoutTracking.hasUserChanges) {
        history.push(trackingData);
    } else {
        history.push(trackingData);
    }

    // Keep last 50 entries
    if (history.length > 50) {
        history.shift();
    }

    localStorage.setItem('layoutTrainingData', JSON.stringify(history));
}

function exportLayoutTrainingData() {
    const data = JSON.parse(localStorage.getItem('layoutTrainingData') || '[]');
    console.log('=== LAYOUT TRAINING DATA EXPORT ===');
    console.log(JSON.stringify(data, null, 2));
    console.log('===================================');

    // Also create downloadable file
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `layout-training-data-${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    URL.revokeObjectURL(url);

    return data;
}

function clearLayoutTrainingData() {
    localStorage.removeItem('layoutTrainingData');
    console.log('Layout training data cleared');
}

function getLayoutComparison() {
    const { chartConfigs, renderedLayout, userLayout, hasUserChanges } = state.layoutTracking;

    console.log('=== LAYOUT COMPARISON ===');
    console.log('Chart Configs:', JSON.stringify(chartConfigs.map(c => ({
        type: c.type,
        title: c.title,
        labelCount: c.data?.labels?.length || 0
    })), null, 2));
    console.log('');
    console.log('Rendered Layout:', JSON.stringify(renderedLayout, null, 2));
    console.log('');
    console.log('User Layout:', JSON.stringify(userLayout, null, 2));
    console.log('');
    console.log('Has Changes:', hasUserChanges);
    console.log('=========================');

    return { chartConfigs, renderedLayout, userLayout, hasUserChanges };
}

// Expose functions globally for console access
window.exportLayoutTrainingData = exportLayoutTrainingData;
window.clearLayoutTrainingData = clearLayoutTrainingData;
window.getLayoutComparison = getLayoutComparison;

// API Functions
async function fetchApi(endpoint, options = {}) {
    const token = localStorage.getItem('auth_token');
    const response = await fetch(endpoint, {
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            ...options.headers
        },
        ...options
    });

    if (response.status === 401) {
        logout();
        return;
    }

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || 'API request failed');
    }

    return response.json();
}

async function loadProjects() {
    try {
        const params = new URLSearchParams({
            data_source: state.dataSource,
            module: state.module,
        });
        const data = await fetchApi(`/api/projects?${params}`);
        const selector = elements.projectSelector;

        // Clear existing options (keep the "All Projects" default)
        while (selector.options.length > 1) {
            selector.remove(1);
        }
        state.currentProject = null;
        selector.value = '';

        data.projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.project_id;
            option.textContent = project.project_name;
            selector.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load projects:', error);
    }
}

function setDataSource(source) {
    state.dataSource = source;

    const activeClass = 'px-3 py-1.5 text-xs font-medium rounded-md bg-white text-blue-700 shadow-sm transition-all';
    const inactiveClass = 'px-3 py-1.5 text-xs font-medium rounded-md text-gray-600 transition-all';

    // Toggle active button styling
    if (elements.sourceAcc && elements.sourceKrion6d) {
        elements.sourceAcc.className = source === 'acc' ? activeClass : inactiveClass;
        elements.sourceKrion6d.className = source === 'krion6d' ? activeClass : inactiveClass;
        if (elements.sourceErp) {
            elements.sourceErp.className = source === 'erp' ? activeClass : inactiveClass;
        }
    }

    // Update prompts for this data source
    buildPromptsDropdown();

    // Clear dashboard and show empty state
    clearDashboard();
    showEmptyState();

    // When switching to ACC, check if connected
    if (source === 'acc') {
        checkAccConnection().then(connected => {
            if (!connected) {
                showAccModal();
            } else {
                loadProjects();
            }
        });
    } else if (source === 'erp') {
        // ERP doesn't have projects — hide project selector, hide ACC indicator
        if (elements.accStatusIndicator) elements.accStatusIndicator.classList.add('hidden');
        if (elements.projectSelector) {
            elements.projectSelector.innerHTML = '<option value="">ERP Data</option>';
            elements.projectSelector.disabled = true;
        }
        state.currentProject = null;
    } else {
        // Hide ACC status indicator for non-ACC sources
        if (elements.accStatusIndicator) elements.accStatusIndicator.classList.add('hidden');
        if (elements.projectSelector) elements.projectSelector.disabled = false;
        loadProjects();
    }
}

// Expose globally so onclick in HTML works
window.setDataSource = setDataSource;

// Sample prompts per data source
const samplePrompts = {
    acc: [
        { category: 'Projects', prompts: [
            'List all ACC projects',
            'How many projects are active?',
        ]},
        { category: 'Issues', prompts: [
            'Show open issues by status',
            'How many issues are assigned to each person?',
            'Which issues are overdue?',
        ]},
        { category: 'RFIs', prompts: [
            'Show RFI status breakdown',
            'Overdue RFIs',
            'RFIs by priority',
        ]},
        { category: 'Submittals', prompts: [
            'Submittal status summary',
            'Show pending submittals',
        ]},
    ],
    krion6d: [
        { category: 'Projects', prompts: [
            'List all projects with their status',
            'How many projects are active?',
        ]},
        { category: 'Issues', prompts: [
            'Show open issues by status',
            'How many issues are assigned to each person?',
            'Which issues are overdue?',
        ]},
        { category: 'RFIs', prompts: [
            'Show RFI status breakdown',
            'Overdue RFIs',
            'RFIs by priority',
        ]},
        { category: 'Tasks & Schedule', prompts: [
            'Show delayed tasks',
            'Task completion summary',
        ]},
        { category: 'Submittals & Transmittals', prompts: [
            'Submittal status summary',
            'Show all transmittals',
        ]},
    ],
    erp: [
        { category: 'Cost Forecast', prompts: [
            'What will be the cost for the upcoming week?',
            'Show cost estimate for next month',
            'Total project cost breakdown',
        ]},
        { category: 'Project Plan', prompts: [
            'Show all tasks in the project plan',
            'Which tasks are scheduled for next week?',
            'Show tasks by responsibility',
        ]},
        { category: 'Bill of Materials', prompts: [
            'Show BOM breakdown by WBS category',
            'What materials are needed for substructure work?',
            'Top 5 most expensive BOM items',
        ]},
        { category: 'ERP Costing', prompts: [
            'Show material cost summary with GST',
            'Which materials have the highest cost?',
            'Total procurement cost breakdown',
        ]},
    ],
};

function buildPromptsDropdown() {
    const container = document.getElementById('prompts-content');
    if (!container) return;

    const prompts = samplePrompts[state.dataSource] || samplePrompts.acc;
    const btnClass = 'sample-query w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 rounded transition-colors';

    let html = '';
    prompts.forEach((group, i) => {
        const mt = i > 0 ? ' mt-2' : '';
        html += `<p class="text-xs text-gray-500 font-medium px-2 py-1${mt} uppercase tracking-wide">${group.category}</p>`;
        group.prompts.forEach(prompt => {
            html += `<button class="${btnClass}">${prompt}</button>`;
        });
    });

    container.innerHTML = html;
}

async function checkHealth() {
    try {
        const data = await fetchApi('/api/health');
        updateStatusIndicator(data.orchestrator_ready);
        return data;
    } catch (error) {
        updateStatusIndicator(false);
        return null;
    }
}

async function submitQuery(query) {
    if (state.isLoading) return;

    setLoading(true);
    clearDashboard();
    hideChatEmptyState();
    clearLiveLog();

    // Hide timeline from previous query
    elements.interactionTimeline.classList.add('hidden');

    // Show chat messages container and add user message
    if (elements.chatMessages) {
        elements.chatMessages.classList.remove('hidden');
        elements.chatMessages.style.display = 'flex';
        console.log('Chat messages container shown');
    }
    addChatMessage(query, 'user');

    // Clear input
    elements.queryInput.value = '';
    elements.clearInputBtn.classList.add('hidden');

    try {
        state.lastQuery = query;
        const authUser = JSON.parse(localStorage.getItem('auth_user') || '{}');
        const payload = {
            query: query,
            project_id: state.currentProject || null,
            data_source: state.dataSource,
            module: state.module,
            user_id: authUser.userID || null,
        };

        const response = await fetchApi('/api/query', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        displayResponse(response);
    } catch (error) {
        showError(error.message);
        addChatMessage('Sorry, an error occurred: ' + error.message, 'agent');
    } finally {
        setLoading(false);
    }
}

// Display Functions
function resetResponseSection() {
    elements.routingInfo.classList.add('hidden');
    elements.agentResponseSection.classList.add('hidden');
    elements.interactionTimeline.classList.add('hidden');
    if (elements.dataSources) {
        elements.dataSources.classList.add('hidden');
    }
    elements.selectedAgents.innerHTML = '';
}

function resetDashboardEmptyStateCopy() {
    const t = document.getElementById('empty-state-title');
    const s = document.getElementById('empty-state-subtitle');
    if (t) t.textContent = 'No data to display';
    if (s) s.textContent = 'Ask a question to generate insights and visualizations';
}

function showDashboardNoChartsHint(hasMessage) {
    resetDashboardEmptyStateCopy();
    const t = document.getElementById('empty-state-title');
    const s = document.getElementById('empty-state-subtitle');
    if (hasMessage) {
        if (t) t.textContent = 'No chart for this answer';
        if (s) s.textContent = 'The summary is in the chat panel. Try asking for a breakdown or chart, e.g. “RFI status breakdown” or “show RFIs by priority”.';
    }
    showEmptyState();
}

function displayResponse(response) {
    console.log('Response received:', response);

    hideChatEmptyState();

    // Ensure chat messages container is visible
    if (elements.chatMessages) {
        elements.chatMessages.classList.remove('hidden');
        elements.chatMessages.style.display = 'flex';
    }

    // Display routing info (intent & agent selection)
    if (response.routing) {
        displayRoutingInfo(response.routing);
    }

    // Display message/insights as chat message
    if (response.message) {
        state.lastSummary = response.message;
        displayMessage(response.message);
    } else if (response.response) {
        // Fallback to 'response' field if 'message' doesn't exist
        state.lastSummary = response.response;
        displayMessage(response.response);
    } else if (response.result) {
        // Fallback to 'result' field
        state.lastSummary = response.result;
        displayMessage(response.result);
    } else {
        // Show something if no message found
        state.lastSummary = '';
        displayMessage('Response received. Check the dashboard for visualizations.');
    }

    // Display data sources reference
    if (response.interaction_logs && response.interaction_logs.length > 0) {
        displayDataSources(response.interaction_logs);
    }

    // Display interaction timeline
    if (response.interaction_logs && response.interaction_logs.length > 0) {
        displayInteractionTimeline(response.interaction_logs, response.interaction_summary);
    }

    // Display charts (left panel stays empty if API returns no chart configs)
    if (response.charts && response.charts.length > 0) {
        displayCharts(response.charts);
        resetDashboardEmptyStateCopy();
    } else {
        showDashboardNoChartsHint(Boolean(response.message || response.response || response.result));
    }

    // Display follow-up questions
    if (response.follow_up_questions && response.follow_up_questions.length > 0) {
        displayFollowUpQuestions(response.follow_up_questions);
    }

    // Scroll chat to bottom
    setTimeout(() => {
        elements.responseSection.scrollTop = elements.responseSection.scrollHeight;
    }, 100);
}

function displayRoutingInfo(routing) {
    // Store routing info but don't display it visually
    if (elements.detectedIntent) {
        elements.detectedIntent.textContent = routing.intent || '';
    }
    if (elements.routingReasoning) {
        elements.routingReasoning.textContent = routing.reasoning || '';
    }
}

function displayMessage(message) {
    if (!message) {
        addChatMessage('No insights available', 'agent');
        return;
    }

    addChatMessage(message, 'agent');
}

function addChatMessage(content, type) {
    console.log('Adding chat message:', type, content);

    if (!elements.chatMessages) {
        console.error('chatMessages element not found!');
        return;
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;

    if (type === 'user') {
        messageDiv.innerHTML = `<div class="chat-message-wrapper"><span class="chat-message-label">You</span><div class="chat-bubble"><p>${escapeHtml(content)}</p></div></div>`;
    } else {
        // Format agent message with markdown-like styling
        let formatted = String(content)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');

        messageDiv.innerHTML = `<div class="agent-avatar"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg></div><div class="chat-message-wrapper"><span class="chat-message-label">Agent</span><div class="chat-bubble"><p>${formatted}</p></div></div>`;
    }

    elements.chatMessages.appendChild(messageDiv);
    console.log('Message appended to chatMessages');

    // Scroll to bottom
    setTimeout(() => {
        elements.responseSection.scrollTop = elements.responseSection.scrollHeight;
    }, 50);
}

function displayFollowUpQuestions(questions) {
    if (!elements.chatMessages || !questions || questions.length === 0) return;

    const container = document.createElement('div');
    container.className = 'follow-up-container';

    const label = document.createElement('div');
    label.className = 'follow-up-label';
    label.textContent = 'Follow-ups';
    container.appendChild(label);

    questions.forEach(q => {
        const chip = document.createElement('button');
        chip.className = 'follow-up-chip';
        chip.textContent = q;
        chip.addEventListener('click', () => {
            elements.queryInput.value = q;
            handleQuerySubmit();
        });
        container.appendChild(chip);
    });

    elements.chatMessages.appendChild(container);

    setTimeout(() => {
        elements.responseSection.scrollTop = elements.responseSection.scrollHeight;
    }, 50);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function displayDataSources(logs) {
    // Extract source files from tool_result logs
    const sources = new Map(); // Use Map to deduplicate by table name

    logs.forEach(log => {
        if (log.type === 'tool_result' && log.details) {
            const details = log.details;
            // Check if details has source_file info
            if (details.source_file && details.table) {
                sources.set(details.table, {
                    table: details.table,
                    source_file: details.source_file,
                    rows: details.total_rows || details.returned_rows || 0
                });
            }
        }
    });

    if (sources.size === 0) {
        elements.dataSources.classList.add('hidden');
        return;
    }

    elements.dataSources.classList.remove('hidden');

    // Display summary
    const sourcesList = Array.from(sources.values());
    const summaryText = `${sourcesList.length} data source${sourcesList.length > 1 ? 's' : ''} used`;
    elements.sourcesSummary.textContent = summaryText;

    // Clear and populate sources container
    elements.sourcesContainer.innerHTML = '';

    sourcesList.forEach(source => {
        const item = document.createElement('div');
        item.className = 'flex items-center justify-between p-2 bg-white rounded border border-gray-200 text-xs';

        const left = document.createElement('div');
        left.className = 'flex items-center space-x-2';

        const icon = document.createElement('span');
        icon.innerHTML = `<svg class="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
        </svg>`;

        const info = document.createElement('div');
        info.innerHTML = `
            <div class="font-medium text-gray-700">${source.table}</div>
            <div class="text-gray-400 text-xs">${source.source_file}</div>
        `;

        left.appendChild(icon);
        left.appendChild(info);

        const right = document.createElement('span');
        right.className = 'text-gray-500';
        right.textContent = source.rows ? `${source.rows} rows` : '';

        item.appendChild(left);
        item.appendChild(right);
        elements.sourcesContainer.appendChild(item);
    });
}

function displayInteractionTimeline(logs, summary) {
    elements.interactionTimeline.classList.remove('hidden');

    // Display summary
    if (summary) {
        const summaryText = `${summary.total_steps} steps | ${summary.tool_calls} tool calls | ${Math.round(summary.total_duration_ms)}ms`;
        elements.timelineSummary.textContent = summaryText;
    }

    // Clear and populate timeline container
    elements.timelineContainer.innerHTML = '';

    logs.forEach(log => {
        const item = createTimelineItem(log);
        elements.timelineContainer.appendChild(item);
    });
}

function createTimelineItem(log) {
    const config = interactionConfig[log.type] || { color: 'gray', label: 'Log' };

    const item = document.createElement('div');
    item.className = 'timeline-item flex items-start space-x-3 p-2 rounded hover:bg-white transition-colors text-xs border-l-2 border-transparent hover:border-' + config.color + '-400';

    // Color indicator
    const indicator = document.createElement('span');
    indicator.className = `flex-shrink-0 w-2 h-2 mt-1.5 rounded-full bg-${config.color}-400`;

    // Content
    const content = document.createElement('div');
    content.className = 'flex-1 min-w-0';

    // Header row
    const header = document.createElement('div');
    header.className = 'flex items-center flex-wrap gap-2';

    const label = document.createElement('span');
    label.className = 'font-medium text-gray-700';
    label.textContent = config.label;
    header.appendChild(label);

    if (log.agent) {
        const agentBadge = document.createElement('span');
        agentBadge.className = 'px-1.5 py-0.5 bg-gray-200 text-gray-600 rounded text-xs';
        agentBadge.textContent = log.agent;
        header.appendChild(agentBadge);
    }

    if (log.duration_ms) {
        const duration = document.createElement('span');
        duration.className = 'text-gray-400 ml-auto';
        duration.textContent = `${Math.round(log.duration_ms)}ms`;
        header.appendChild(duration);
    }

    // Message
    const message = document.createElement('p');
    message.className = 'text-gray-500 truncate mt-0.5';
    message.textContent = log.message;
    message.title = log.message;

    content.appendChild(header);
    content.appendChild(message);

    // Details (expandable)
    if (log.details && Object.keys(log.details).length > 0) {
        const details = document.createElement('pre');
        details.className = 'mt-2 text-xs text-gray-400 hidden details-content bg-white border border-gray-200 p-2 rounded overflow-x-auto';
        details.textContent = JSON.stringify(log.details, null, 2);
        content.appendChild(details);

        item.classList.add('cursor-pointer');
        item.addEventListener('click', () => {
            details.classList.toggle('hidden');
        });
    }

    item.appendChild(indicator);
    item.appendChild(content);

    return item;
}

function addLiveLogItem(message, type = 'info') {
    const config = interactionConfig[type] || { color: 'gray' };

    const item = document.createElement('div');
    item.className = 'flex items-center space-x-2 text-xs';
    item.innerHTML = `
        <span class="w-1.5 h-1.5 rounded-full bg-${config.color}-400"></span>
        <span class="text-gray-600 truncate">${message}</span>
    `;

    elements.liveLog.appendChild(item);
    elements.liveLog.scrollTop = elements.liveLog.scrollHeight;
}

function clearLiveLog() {
    elements.liveLog.innerHTML = '';
}

function displayCharts(charts) {
    // Hide empty state when charts are loaded
    hideEmptyState();

    // Clear existing charts (but not the widgetConfigs - they get repopulated below)
    clearDashboard();

    // Store chart configs for training data
    state.layoutTracking.chartConfigs = charts.map(c => ({
        type: c.type,
        title: c.title,
        labelCount: c.data?.labels?.length || 0,
        datasetCount: c.data?.datasets?.length || 0,
        // For tables, include row/column counts
        rowCount: c.data?.rows?.length || 0,
        columnCount: c.data?.headers?.length || 0
    }));

    // Analyze charts to determine adaptive layout
    const layoutInfo = analyzeChartsForLayout(charts);

    charts.forEach((chartConfig, index) => {
        createChartWidget(chartConfig, index, layoutInfo);
    });

    // Show the "Export All" buttons
    const exportAllBtn = document.getElementById('export-all-btn');
    if (exportAllBtn) {
        exportAllBtn.classList.remove('hidden');
        exportAllBtn.classList.add('flex');
    }

    // Capture rendered layout after widgets are placed
    captureRenderedLayout();
}

function analyzeChartsForLayout(charts) {
    // Separate chart types with their original indices
    const kpis = charts.map((c, i) => ({ ...c, idx: i })).filter(c => c.type === 'kpi');
    const pies = charts.map((c, i) => ({ ...c, idx: i })).filter(c => c.type === 'pie' || c.type === 'doughnut');
    const bars = charts.map((c, i) => ({ ...c, idx: i })).filter(c => c.type === 'bar' || c.type === 'line');
    const tables = charts.map((c, i) => ({ ...c, idx: i })).filter(c => c.type === 'table');

    const chartWidths = {};
    const chartHeights = {};
    const chartPositions = {};

    // Pattern: KPI + Pie/Doughnut side by side, Bar full width below
    const hasKpiPieBarPattern = kpis.length >= 1 && pies.length >= 1 && bars.length >= 1;

    if (hasKpiPieBarPattern) {
        let currentY = 0;
        let rowX = 0;

        // Calculate pie sizes based on label count
        pies.forEach(pie => {
            const labelCount = pie.data?.labels?.length || 0;
            // More labels = more width needed for legend
            if (labelCount <= 2) {
                pie._calcWidth = 4;
                pie._calcHeight = 5;
            } else if (labelCount <= 4) {
                pie._calcWidth = 5;
                pie._calcHeight = 5;
            } else if (labelCount <= 6) {
                pie._calcWidth = 6;
                pie._calcHeight = 6;
            } else {
                pie._calcWidth = 8;
                pie._calcHeight = 7;
            }
        });

        // Calculate bar sizes based on label count
        bars.forEach(bar => {
            const labelCount = bar.data?.labels?.length || 0;
            if (labelCount <= 4) {
                bar._calcWidth = 6;
                bar._calcHeight = 5;
            } else if (labelCount <= 8) {
                bar._calcWidth = 8;
                bar._calcHeight = 6;
            } else {
                bar._calcWidth = 12;
                bar._calcHeight = 7;
            }
        });

        // Determine layout based on sizes
        const totalPieWidth = pies.reduce((sum, p) => sum + p._calcWidth, 0);
        const totalKpiWidth = kpis.length * 4;
        const maxPieHeight = Math.max(...pies.map(p => p._calcHeight), 5);
        const maxBarHeight = Math.max(...bars.map(b => b._calcHeight), 5);

        // Check if KPIs + Pies can fit in one row
        const canFitInOneRow = (totalKpiWidth + totalPieWidth) <= 12;

        if (canFitInOneRow) {
            // Row 1: KPIs + Pies side by side
            kpis.forEach(kpi => {
                chartWidths[kpi.idx] = 4;
                chartHeights[kpi.idx] = maxPieHeight;
                chartPositions[kpi.idx] = { x: rowX, y: currentY };
                rowX += 4;
            });

            pies.forEach(pie => {
                // Expand last pie to fill remaining space
                const isLast = pie === pies[pies.length - 1];
                const width = isLast ? (12 - rowX) : pie._calcWidth;
                chartWidths[pie.idx] = width;
                chartHeights[pie.idx] = maxPieHeight;
                chartPositions[pie.idx] = { x: rowX, y: currentY };
                rowX += width;
            });

            currentY += maxPieHeight;
        } else {
            // KPIs in first row, Pies in second row
            kpis.forEach(kpi => {
                const kpiWidth = Math.floor(12 / kpis.length);
                chartWidths[kpi.idx] = kpiWidth;
                chartHeights[kpi.idx] = 3;
                chartPositions[kpi.idx] = { x: rowX, y: currentY };
                rowX += kpiWidth;
            });
            currentY += 3;
            rowX = 0;

            pies.forEach(pie => {
                chartWidths[pie.idx] = pie._calcWidth;
                chartHeights[pie.idx] = pie._calcHeight;
                chartPositions[pie.idx] = { x: rowX, y: currentY };
                rowX += pie._calcWidth;
                if (rowX >= 12) {
                    currentY += pie._calcHeight;
                    rowX = 0;
                }
            });
            if (rowX > 0) currentY += maxPieHeight;
        }

        // Bars: full width below
        bars.forEach(bar => {
            chartWidths[bar.idx] = 12;
            chartHeights[bar.idx] = bar._calcHeight;
            chartPositions[bar.idx] = { x: 0, y: currentY };
            currentY += bar._calcHeight;
        });

        // Tables at the bottom
        tables.forEach(table => {
            chartWidths[table.idx] = 12;
            chartHeights[table.idx] = 6;
            chartPositions[table.idx] = { x: 0, y: currentY };
            currentY += 6;
        });

    } else if (kpis.length >= 2 && pies.length >= 1) {
        // Multiple KPIs with pie: KPIs in row, pie + bar below
        const kpiWidth = Math.floor(12 / kpis.length);
        let currentY = 0;

        kpis.forEach((kpi, i) => {
            chartWidths[kpi.idx] = kpiWidth;
            chartHeights[kpi.idx] = 3;
            chartPositions[kpi.idx] = { x: i * kpiWidth, y: 0 };
        });
        currentY = 3;

        // Pies and bars below
        pies.forEach(pie => {
            chartWidths[pie.idx] = 6;
            chartHeights[pie.idx] = 5;
            chartPositions[pie.idx] = { x: 0, y: currentY };
        });

        bars.forEach((bar, i) => {
            chartWidths[bar.idx] = 6;
            chartHeights[bar.idx] = 5;
            chartPositions[bar.idx] = { x: 6, y: currentY };
        });

        if (pies.length > 0 || bars.length > 0) currentY += 5;

        tables.forEach(table => {
            chartWidths[table.idx] = 12;
            chartHeights[table.idx] = 6;
            chartPositions[table.idx] = { x: 0, y: currentY };
            currentY += 6;
        });

    } else {
        // Fallback: standard flow layout
        charts.forEach((chart, idx) => {
            if (chart.type === 'kpi') {
                chartWidths[idx] = kpis.length === 1 ? 4 : kpis.length === 2 ? 6 : 4;
                chartHeights[idx] = 3;
            } else if (chart.type === 'table') {
                chartWidths[idx] = 12;
                chartHeights[idx] = 6;
            } else {
                const labelCount = chart.data?.labels?.length || 0;
                if (chart.type === 'pie' || chart.type === 'doughnut') {
                    chartWidths[idx] = labelCount <= 3 ? 4 : labelCount <= 6 ? 6 : 8;
                    chartHeights[idx] = 5;
                } else {
                    chartWidths[idx] = labelCount <= 4 ? 6 : labelCount <= 7 ? 8 : 12;
                    chartHeights[idx] = labelCount > 8 ? 6 : 5;
                }
            }
        });

        optimizeRowFilling(charts, chartWidths);
        return {
            kpiCount: kpis.length,
            chartWidths,
            chartHeights,
            chartPositions: {},
            usePositions: false,
            totalCharts: charts.length
        };
    }

    return {
        kpiCount: kpis.length,
        chartWidths,
        chartHeights,
        chartPositions,
        usePositions: true,
        totalCharts: charts.length
    };
}

function optimizeRowFilling(charts, chartWidths) {
    // Group charts by approximate row position and adjust to fill 12 cols
    let currentRowWidth = 0;
    let rowCharts = [];

    for (let i = 0; i < charts.length; i++) {
        const width = chartWidths[i];

        if (currentRowWidth + width <= 12) {
            currentRowWidth += width;
            rowCharts.push(i);
        } else {
            // Finalize previous row
            finalizeRow(charts, chartWidths, rowCharts, currentRowWidth);
            // Start new row
            currentRowWidth = width;
            rowCharts = [i];
        }
    }

    // Handle final row
    finalizeRow(charts, chartWidths, rowCharts, currentRowWidth);
}

function finalizeRow(charts, chartWidths, rowCharts, currentRowWidth) {
    if (rowCharts.length === 0 || currentRowWidth >= 12) return;

    const gap = 12 - currentRowWidth;

    // If single chart in row and it's not a table, expand it
    if (rowCharts.length === 1) {
        const idx = rowCharts[0];
        if (charts[idx].type !== 'table') {
            chartWidths[idx] = 12;
        }
        return;
    }

    // Multiple charts - try to expand non-KPI, non-table charts to fill gap
    if (gap <= 6) {
        // Find best chart to expand (prefer bar/line over pie/doughnut)
        let expandIdx = -1;
        for (const idx of rowCharts) {
            const type = charts[idx].type;
            if (type === 'bar' || type === 'line') {
                expandIdx = idx;
                break;
            } else if (type === 'pie' || type === 'doughnut') {
                if (expandIdx === -1) expandIdx = idx;
            }
        }
        if (expandIdx >= 0) {
            chartWidths[expandIdx] += gap;
        }
    }
}

function getChartTypeIcon(type) {
    const icons = {
        kpi: `<svg class="widget-title-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
        </svg>`,
        bar: `<svg class="widget-title-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
        </svg>`,
        pie: `<svg class="widget-title-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"></path>
        </svg>`,
        doughnut: `<svg class="widget-title-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"></path>
        </svg>`,
        line: `<svg class="widget-title-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"></path>
        </svg>`,
        table: `<svg class="widget-title-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
        </svg>`
    };
    return icons[type] || icons.bar;
}

function createChartWidget(config, index, layoutInfo = null) {
    const widgetId = `widget-${Date.now()}-${index}`;
    const chartId = `chart-${widgetId}`;

    // Use adaptive width/height from layoutInfo
    let width = layoutInfo?.chartWidths?.[index] || 6;
    let height = layoutInfo?.chartHeights?.[index] || 5;

    // Get position if using positioned layout
    let x = layoutInfo?.chartPositions?.[index]?.x;
    let y = layoutInfo?.chartPositions?.[index]?.y;

    // Fallback height if not in layoutInfo
    if (!layoutInfo?.chartHeights?.[index]) {
        if (config.type === 'kpi') {
            height = 3;
        } else if (config.type === 'table') {
            width = 12;
            height = 6;
        } else if (config.type === 'pie' || config.type === 'doughnut') {
            const labelCount = config.data?.labels?.length || 0;
            height = labelCount > 6 ? 7 : 5;
        } else if (config.type === 'bar') {
            const labelCount = config.data?.labels?.length || 0;
            height = labelCount > 8 ? 6 : 5;
        } else if (config.type === 'line') {
            height = 5;
        }
    }

    // Get chart type icon
    const iconSvg = getChartTypeIcon(config.type);

    // Create widget HTML
    let contentHtml;

    if (config.type === 'kpi') {
        contentHtml = createKpiContent(config);
    } else if (config.type === 'table') {
        contentHtml = createTableContent(config);
    } else {
        contentHtml = `<canvas id="${chartId}"></canvas>`;
    }

    // Store config for CSV export
    state.widgetConfigs[widgetId] = config;

    const widgetHtml = `
        <div class="grid-stack-item-content bg-white rounded-xl border border-gray-200 p-3 h-full">
            <div class="flex items-center justify-between mb-2">
                <h3 class="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
                    ${iconSvg}
                    <span>${config.title || 'Chart'}</span>
                </h3>
                <div class="flex items-center space-x-1">
                    <button class="widget-export text-gray-400 hover:text-blue-600 transition-colors p-1" data-widget="${widgetId}" title="Export CSV">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                    </button>
                    <button class="widget-close text-gray-400 hover:text-red-500 transition-colors p-1" data-widget="${widgetId}">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
            </div>
            <div class="chart-content" style="height: calc(100% - 32px); width: 100%;">
                ${contentHtml}
            </div>
        </div>
    `;

    // Add to grid with position if specified
    const widgetOptions = {
        w: width,
        h: height,
        content: widgetHtml,
        id: widgetId
    };

    // Use explicit positions for stacked layouts
    if (x !== undefined && y !== undefined) {
        widgetOptions.x = x;
        widgetOptions.y = y;
    }

    const widget = state.grid.addWidget(widgetOptions);

    // Create chart if needed
    if (!['kpi', 'table'].includes(config.type)) {
        setTimeout(() => {
            const canvas = document.getElementById(chartId);
            if (canvas) {
                createChart(canvas, config);
            }
        }, 100);
    }

    // Add export button handler
    widget.querySelector('.widget-export')?.addEventListener('click', (e) => {
        e.stopPropagation();
        const wId = e.currentTarget.dataset.widget;
        exportWidgetCsv(wId);
    });

    // Add close button handler
    widget.querySelector('.widget-close')?.addEventListener('click', (e) => {
        const wId = e.currentTarget.dataset.widget;
        const widgetEl = document.querySelector(`[gs-id="${wId}"]`);
        if (widgetEl) {
            delete state.widgetConfigs[wId];
            state.grid.removeWidget(widgetEl);
        }
    });
}

function createKpiContent(config) {
    const data = config.data || {};

    // Determine trend styling
    let trendClass = 'text-gray-500 bg-gray-100';
    let trendIcon = '';

    if (data.trend === 'up') {
        trendClass = 'text-green-600 bg-green-50';
        trendIcon = '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"></path></svg>';
    } else if (data.trend === 'down') {
        trendClass = 'text-red-600 bg-red-50';
        trendIcon = '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path></svg>';
    }

    return `
        <div class="flex flex-col items-center justify-center h-full w-full text-center p-2">
            <div class="text-3xl font-bold text-gray-900">${data.value}</div>
            ${data.unit ? `<div class="text-sm font-medium text-gray-500 mt-1">${data.unit}</div>` : ''}
            ${data.change ? `
                <div class="flex items-center gap-1 mt-2 px-2 py-0.5 rounded-full text-xs font-medium ${trendClass}">
                    ${trendIcon}
                    <span>${data.change}</span>
                </div>
            ` : ''}
            ${data.subtitle ? `<div class="text-xs text-gray-400 mt-1">${data.subtitle}</div>` : ''}
        </div>
    `;
}

function createTableContent(config) {
    const data = config.data || {};
    const headers = data.headers || [];
    const rows = data.rows || [];

    let html = '<div class="overflow-auto h-full w-full rounded border border-gray-200">';
    html += '<table class="min-w-full divide-y divide-gray-200 text-xs">';

    // Header
    html += '<thead class="bg-gray-50 sticky top-0"><tr>';
    headers.forEach((header, idx) => {
        const align = idx === 0 ? 'text-left' : 'text-right';
        html += `<th class="px-4 py-3 ${align} text-xs font-semibold text-gray-600 uppercase tracking-wider">${header}</th>`;
    });
    html += '</tr></thead>';

    // Body
    html += '<tbody class="bg-white divide-y divide-gray-100">';
    rows.forEach((row, rowIdx) => {
        const bgClass = rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50';
        html += `<tr class="${bgClass} hover:bg-blue-50 transition-colors">`;
        row.forEach((cell, cellIdx) => {
            const align = cellIdx === 0 ? 'text-left font-medium text-gray-900' : 'text-right text-gray-600';
            html += `<td class="px-4 py-2.5 whitespace-nowrap ${align}">${cell}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody></table></div>';

    return html;
}

function createChart(canvas, config) {
    const ctx = canvas.getContext('2d');

    // Default colors
    const defaultColors = [
        'rgba(59, 130, 246, 0.8)',
        'rgba(16, 185, 129, 0.8)',
        'rgba(245, 158, 11, 0.8)',
        'rgba(239, 68, 68, 0.8)',
        'rgba(139, 92, 246, 0.8)',
        'rgba(236, 72, 153, 0.8)',
        'rgba(20, 184, 166, 0.8)',
        'rgba(249, 115, 22, 0.8)'
    ];

    // Ensure datasets have colors
    if (config.data && config.data.datasets) {
        config.data.datasets.forEach((dataset, i) => {
            if (!dataset.backgroundColor) {
                if (['pie', 'doughnut'].includes(config.type)) {
                    dataset.backgroundColor = defaultColors.slice(0, config.data.labels?.length || 5);
                } else {
                    dataset.backgroundColor = defaultColors[i % defaultColors.length];
                }
            }
            if (!dataset.borderColor && ['line', 'bar'].includes(config.type)) {
                const bg = dataset.backgroundColor;
                if (typeof bg === 'string') {
                    dataset.borderColor = bg.replace('0.8', '1');
                } else if (Array.isArray(bg)) {
                    dataset.borderColor = bg.map(c => c.replace('0.8', '1'));
                }
            }
        });
    }

    const chartConfig = {
        type: config.type,
        data: config.data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: ['pie', 'doughnut', 'line'].includes(config.type),
                    position: 'right'
                }
            },
            ...(config.options || {})
        }
    };

    const chartInstance = new Chart(ctx, chartConfig);
    state.charts[canvas.id] = chartInstance;

    return chartInstance;
}

// UI Helper Functions
function setLoading(loading) {
    state.isLoading = loading;
    elements.queryBtn.disabled = loading;
    elements.queryBtnText.classList.toggle('hidden', loading);
    elements.queryBtnSpinner.classList.toggle('hidden', !loading);
    elements.processingStatus.classList.toggle('hidden', !loading);

    if (loading) {
        updateProcessingStatus('Processing...', 'Analyzing your query');
    }
}

function updateProcessingStatus(message, detail) {
    elements.processingMessage.textContent = message;
    elements.processingDetail.textContent = detail;
}

function showError(message) {
    elements.errorMessage.textContent = message;
    elements.errorToast.classList.remove('translate-y-full', 'opacity-0');

    setTimeout(() => {
        elements.errorToast.classList.add('translate-y-full', 'opacity-0');
    }, 5000);
}

function hideEmptyState() {
    if (elements.emptyState) {
        elements.emptyState.style.display = 'none';
    }
}

function showEmptyState() {
    if (elements.emptyState) {
        elements.emptyState.style.display = 'flex';
    }
}

function hideChatEmptyState() {
    if (elements.chatEmptyState) {
        elements.chatEmptyState.style.display = 'none';
    }
}

function showChatEmptyState() {
    if (elements.chatEmptyState) {
        elements.chatEmptyState.style.display = 'flex';
    }
}

function updateStatusIndicator(connected) {
    const dot = elements.statusIndicator.querySelector('span:first-child');
    const text = elements.statusIndicator.querySelector('span:last-child');

    if (connected) {
        dot.classList.remove('bg-red-500');
        dot.classList.add('bg-green-500');
        text.textContent = 'Connected';
    } else {
        dot.classList.remove('bg-green-500');
        dot.classList.add('bg-red-500');
        text.textContent = 'Disconnected';
    }
}

function clearDashboard() {
    // Destroy all charts
    Object.values(state.charts).forEach(chart => {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    });
    state.charts = {};
    state.widgetConfigs = {};

    // Remove all widgets
    if (state.grid) {
        state.grid.removeAll();
    }

    // Hide the "Export All" buttons
    const exportAllBtn = document.getElementById('export-all-btn');
    if (exportAllBtn) {
        exportAllBtn.classList.add('hidden');
        exportAllBtn.classList.remove('flex');
    }
}

function toggleTimelineExpanded() {
    state.timelineExpanded = !state.timelineExpanded;
    elements.timelineContainer.classList.toggle('hidden', !state.timelineExpanded);
    elements.toggleTimeline.textContent = state.timelineExpanded ? 'Hide details' : 'Show details';
}

function toggleSourcesExpanded() {
    state.sourcesExpanded = !state.sourcesExpanded;
    elements.sourcesContainer.classList.toggle('hidden', !state.sourcesExpanded);
    elements.toggleSources.textContent = state.sourcesExpanded ? 'Hide files' : 'Show files';
}

// Event Handlers
function handleQuerySubmit() {
    const query = elements.queryInput.value.trim();
    if (query) {
        submitQuery(query);
    }
}

function handleKeyPress(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleQuerySubmit();
    }
}

function handleInputChange() {
    const hasValue = elements.queryInput.value.length > 0;
    elements.clearInputBtn.classList.toggle('hidden', !hasValue);
}

function handleClearInput() {
    elements.queryInput.value = '';
    elements.clearInputBtn.classList.add('hidden');
    elements.queryInput.focus();
}

function handleProjectChange() {
    state.currentProject = elements.projectSelector.value || null;
}

async function handleReload() {
    try {
        await fetchApi('/api/data/reload', { method: 'POST' });
        await loadProjects();
        showError('Data reloaded successfully');
    } catch (error) {
        showError('Failed to reload data: ' + error.message);
    }
}

function handleSampleQuery(e) {
    if (e.target.classList.contains('sample-query')) {
        const query = e.target.textContent.trim();
        if (query) {
            // Close the dropdown
            hidePromptsDropdown();
            submitQuery(query);
        }
    }
}

function togglePromptsDropdown(e) {
    if (e) {
        e.stopPropagation();
    }
    const isHidden = elements.promptsDropdown.classList.contains('hidden');
    if (isHidden) {
        showPromptsDropdown();
    } else {
        hidePromptsDropdown();
    }
}

function showPromptsDropdown() {
    if (elements.promptsDropdown) elements.promptsDropdown.classList.remove('hidden');
    if (elements.promptsChevron) elements.promptsChevron.classList.add('rotate-180');
}

function hidePromptsDropdown() {
    if (elements.promptsDropdown) elements.promptsDropdown.classList.add('hidden');
    if (elements.promptsChevron) elements.promptsChevron.classList.remove('rotate-180');
}

function handleClickOutside(e) {
    // Close prompts dropdown if clicking outside
    if (elements.viewPromptsBtn && elements.promptsDropdown) {
        if (!elements.viewPromptsBtn.contains(e.target) && !elements.promptsDropdown.contains(e.target)) {
            hidePromptsDropdown();
        }
    }
}

// ---------------------------------------------------------------------------
// CSV Export Functions
// ---------------------------------------------------------------------------

function exportWidgetCsv(widgetId) {
    const config = state.widgetConfigs[widgetId];
    if (!config) {
        showError('No data available to export');
        return;
    }

    const csv = chartConfigToCsv(config);
    if (!csv) {
        showError('Cannot export this widget type');
        return;
    }

    const filename = (config.title || 'chart-data')
        .replace(/[^a-zA-Z0-9 ]/g, '')
        .replace(/\s+/g, '_')
        .toLowerCase();

    downloadCsv(csv, `${filename}.csv`);
}

function chartConfigToCsv(config) {
    const type = config.type;
    const data = config.data;
    if (!data) return null;

    if (type === 'table') {
        return tableToCsv(data);
    }

    if (type === 'kpi') {
        return kpiToCsv(config);
    }

    // bar, line, pie, doughnut – labels + datasets
    if (data.labels && data.datasets) {
        return chartDataToCsv(data);
    }

    return null;
}

function chartDataToCsv(data) {
    const labels = data.labels || [];
    const datasets = data.datasets || [];

    // Header row: Label, Dataset1Name, Dataset2Name, ...
    const header = ['Label', ...datasets.map(ds => csvEscape(ds.label || 'Value'))];
    const rows = [header.join(',')];

    labels.forEach((label, i) => {
        const values = datasets.map(ds => {
            const val = Array.isArray(ds.data) ? ds.data[i] : '';
            return val !== null && val !== undefined ? val : '';
        });
        rows.push([csvEscape(String(label)), ...values].join(','));
    });

    return rows.join('\n');
}

function tableToCsv(data) {
    const headers = data.headers || [];
    const tableRows = data.rows || [];

    const rows = [headers.map(h => csvEscape(String(h))).join(',')];
    tableRows.forEach(row => {
        rows.push(row.map(cell => csvEscape(String(cell !== null && cell !== undefined ? cell : ''))).join(','));
    });

    return rows.join('\n');
}

function kpiToCsv(config) {
    const data = config.data || {};
    const rows = ['Metric,Value'];
    rows.push(`${csvEscape(config.title || 'KPI')},${csvEscape(String(data.value || ''))}`);
    if (data.unit) rows.push(`Unit,${csvEscape(data.unit)}`);
    if (data.change) rows.push(`Change,${csvEscape(data.change)}`);
    if (data.trend) rows.push(`Trend,${csvEscape(data.trend)}`);
    if (data.subtitle) rows.push(`Subtitle,${csvEscape(data.subtitle)}`);
    return rows.join('\n');
}

function csvEscape(value) {
    if (typeof value !== 'string') value = String(value);
    if (value.includes(',') || value.includes('"') || value.includes('\n')) {
        return '"' + value.replace(/"/g, '""') + '"';
    }
    return value;
}

function downloadCsv(csvContent, filename) {
    const BOM = '\uFEFF';
    const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}


// ---------------------------------------------------------------------------
// Backend Export Functions (CSV/XLSX/PDF)
// ---------------------------------------------------------------------------

function sanitizeFilenamePart(value, fallback) {
    return (value || fallback || '')
        .replace(/[<>:"/\\|?*\x00-\x1f]/g, '')
        .replace(/\s+/g, '_')
        .trim() || fallback || 'Unknown';
}

function formatDateForName() {
    const date = new Date();
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function getDashboardDateRange() {
    return 'AllTime';
}

function getChartImageForWidget(widgetId) {
    const widgetEl = document.querySelector(`[gs-id="${widgetId}"]`);
    if (!widgetEl) return null;
    const canvas = widgetEl.querySelector('canvas');
    if (!canvas) return null;
    const chart = state.charts[canvas.id];
    if (!chart || typeof chart.toBase64Image !== 'function') return null;
    try {
        return chart.toBase64Image('image/png', 1);
    } catch (_err) {
        return null;
    }
}

function buildExportSnapshot() {
    const widgets = Object.entries(state.widgetConfigs).map(([widgetId, config]) => ({
        widget_id: widgetId,
        title: config.title || 'Untitled Widget',
        type: config.type,
        data: config.data || {},
        chart_config: config,
        chart_image_base64: getChartImageForWidget(widgetId),
    }));

    const moduleValue = state.module || 'AllModules';
    const projectValue = elements.projectSelector?.selectedOptions?.[0]?.text || state.currentProject || 'AllProjects';

    return {
        metadata: {
            project_code: projectValue,
            module: moduleValue,
            date_range: getDashboardDateRange(),
            data_source: state.dataSource,
            query_text: state.lastQuery || '',
            summary_text: state.lastSummary || '',
            timestamp: new Date().toISOString(),
        },
        widgets,
    };
}

async function requestExportFile(format) {
    const token = localStorage.getItem('auth_token');
    const snapshot = buildExportSnapshot();
    const response = await fetch('/api/export', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ format, snapshot }),
    });
    if (response.status === 401) {
        logout();
        return null;
    }
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Export request failed' }));
        throw new Error(error.detail || 'Export request failed');
    }
    return response;
}

function getFileNameFromHeader(disposition, fallbackName) {
    if (!disposition) return fallbackName;
    const match = disposition.match(/filename=\"?([^\"]+)\"?/i);
    return match?.[1] || fallbackName;
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

function buildFallbackFilename(format) {
    const projectCode = sanitizeFilenamePart(elements.projectSelector?.selectedOptions?.[0]?.text || 'AllProjects', 'AllProjects');
    const moduleName = sanitizeFilenamePart(state.module || 'AllModules', 'AllModules');
    const dateRange = sanitizeFilenamePart(getDashboardDateRange() || formatDateForName(), 'AllTime');
    return `${projectCode}_${moduleName}_${dateRange}_${format}.${format}`;
}

async function exportDashboard(format) {
    if (state.isLoading) return;
    const widgetIds = Object.keys(state.widgetConfigs);
    if (widgetIds.length === 0) {
        showError('No data to export');
        return;
    }

    if (elements.exportAllTrigger) {
        elements.exportAllTrigger.disabled = true;
    }

    try {
        const response = await requestExportFile(format);
        if (!response) return;
        const blob = await response.blob();
        const headerName = getFileNameFromHeader(response.headers.get('content-disposition'), '');
        downloadBlob(blob, headerName || buildFallbackFilename(format));
    } catch (error) {
        showError(error.message || 'Export failed');
    } finally {
        if (elements.exportAllTrigger) {
            elements.exportAllTrigger.disabled = false;
        }
    }
}

async function handleExportClick() {
    const format = elements.exportFormatSelector?.value || 'csv';
    await exportDashboard(format);
}

// ---------------------------------------------------------------------------
// ACC OAuth Functions
// ---------------------------------------------------------------------------

async function checkAccConnection() {
    try {
        const params = new URLSearchParams();
        const data = await fetchApi('/api/acc/status');

        if (data.connected) {
            state.accConnected = true;
            updateAccStatusIndicator(true, data.email || data.user_name);
            return true;
        }
    } catch (e) {
        console.log('ACC status check:', e.message);
    }

    state.accConnected = false;
    updateAccStatusIndicator(false);
    return false;
}

function updateAccStatusIndicator(connected, userInfo) {
    if (!elements.accStatusIndicator) return;

    if (connected && state.dataSource === 'acc') {
        elements.accStatusIndicator.classList.remove('hidden');
        elements.accStatusIndicator.classList.add('flex');
        if (elements.accStatusText && userInfo) {
            elements.accStatusText.textContent = userInfo;
        }
    } else {
        elements.accStatusIndicator.classList.add('hidden');
        elements.accStatusIndicator.classList.remove('flex');
    }
}

function showAccModal() {
    if (!elements.accLoginModal) return;
    elements.accLoginModal.classList.remove('hidden');

    if (state.accConnected) {
        setAccModalState('connected');
    } else {
        setAccModalState('not-connected');
    }
}

function closeAccModal() {
    if (elements.accLoginModal) elements.accLoginModal.classList.add('hidden');
}
window.closeAccModal = closeAccModal;

function setAccModalState(stateName) {
    const states = {
        'not-connected': elements.accModalNotConnected,
        'connecting': elements.accModalConnecting,
        'connected': elements.accModalConnected,
    };

    Object.values(states).forEach(el => { if (el) el.classList.add('hidden'); });
    const target = states[stateName];
    if (target) target.classList.remove('hidden');
}

async function accLogin() {
    try {
        setAccModalState('connecting');

        // 1. Get authorization URL from backend
        const data = await fetchApi('/api/acc/login');
        if (!data.url) throw new Error('No authorization URL returned');

        // 2. Open popup
        const popup = window.open(data.url, 'ACC_Login', 'width=800,height=700,scrollbars=yes');

        // 3. Listen for postMessage from callback page
        const messageHandler = (event) => {
            if (event.data && event.data.type === 'acc-auth-callback') {
                window.removeEventListener('message', messageHandler);
                if (event.data.success) {
                    state.accConnected = true;

                    // Update modal to connected state
                    if (elements.accModalUserInfo) {
                        elements.accModalUserInfo.textContent = event.data.email || event.data.userName || '';
                    }
                    setAccModalState('connected');
                    updateAccStatusIndicator(true, event.data.email || event.data.userName);

                    // Load projects
                    loadProjects();
                } else {
                    setAccModalState('not-connected');
                    showError('ACC login failed: ' + (event.data.error || 'Unknown error'));
                }
            }
        };
        window.addEventListener('message', messageHandler);

        // 4. Fallback: poll for popup close + check status
        const pollInterval = setInterval(async () => {
            if (popup && popup.closed) {
                clearInterval(pollInterval);
                window.removeEventListener('message', messageHandler);
                // Give postMessage a moment to arrive, then check status as fallback
                setTimeout(async () => {
                    if (!state.accConnected) {
                        // Query status without acc_user_id to find newly connected user
                        try {
                            const data = await fetchApi('/api/acc/status');
                            if (data.connected) {
                                state.accConnected = true;
                                const userDisplay = data.email || data.user_name || 'Connected';
                                setAccModalState('connected');
                                if (elements.accModalUserInfo) {
                                    elements.accModalUserInfo.textContent = userDisplay;
                                }
                                updateAccStatusIndicator(true, userDisplay);
                                loadProjects();
                            } else {
                                setAccModalState('not-connected');
                            }
                        } catch (e) {
                            setAccModalState('not-connected');
                        }
                    }
                }, 500);
            }
        }, 500);

    } catch (error) {
        console.error('ACC login error:', error);
        setAccModalState('not-connected');
        showError('ACC login error: ' + error.message);
    }
}
window.accLogin = accLogin;

async function accDisconnect() {
    try {
        await fetchApi('/api/acc/disconnect', { method: 'POST' });
    } catch (e) {
        console.error('ACC disconnect error:', e);
    }

    state.accConnected = false;
    updateAccStatusIndicator(false);

    // Clear project selector
    const selector = elements.projectSelector;
    while (selector.options.length > 1) selector.remove(1);
    state.currentProject = null;

    setAccModalState('not-connected');
}
window.accDisconnect = accDisconnect;


// Initialize
async function init() {
    // Initialize grid
    initGrid();

    // Bind events
    elements.queryBtn.addEventListener('click', handleQuerySubmit);
    elements.queryInput.addEventListener('keypress', handleKeyPress);
    elements.queryInput.addEventListener('input', handleInputChange);
    elements.clearInputBtn.addEventListener('click', handleClearInput);
    elements.projectSelector.addEventListener('change', handleProjectChange);
    elements.reloadBtn.addEventListener('click', handleReload);
    elements.toggleTimeline.addEventListener('click', toggleTimelineExpanded);
    if (elements.toggleSources) {
        elements.toggleSources.addEventListener('click', toggleSourcesExpanded);
    }
    document.addEventListener('click', handleSampleQuery);

    // Module selector change handler
    if (elements.moduleSelector) {
        elements.moduleSelector.addEventListener('change', () => {
            state.module = elements.moduleSelector.value;
            loadProjects();
        });
    }

    // View Prompts dropdown
    if (elements.viewPromptsBtn) {
        elements.viewPromptsBtn.addEventListener('click', togglePromptsDropdown);
    }
    document.addEventListener('click', handleClickOutside);

    if (elements.exportAllTrigger) {
        elements.exportAllTrigger.addEventListener('click', handleExportClick);
    }

    // Show logged-in user name
    try {
        const authUser = JSON.parse(localStorage.getItem('auth_user') || '{}');
        const displayName = authUser.email
            || authUser.username
            || [authUser.firstName, authUser.lastName].filter(Boolean).join(' ')
            || '';
        const emailEl = document.getElementById('logged-in-email');
        if (emailEl && displayName) {
            emailEl.textContent = displayName;
        }
    } catch(e) {}

    // Build initial prompts dropdown
    buildPromptsDropdown();

    // Check health
    await checkHealth();

    // On startup: if ACC mode, check connection first
    if (state.dataSource === 'acc') {
        const connected = await checkAccConnection();
        if (connected) {
            await loadProjects();
        }
        // If not connected, user will see the modal when they interact
    } else {
        await loadProjects();
    }

    // Focus input
    elements.queryInput.focus();
}

// Start app
document.addEventListener('DOMContentLoaded', init);
