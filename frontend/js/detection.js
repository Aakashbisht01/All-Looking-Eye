/**
 * Golden Eye - Detection Interface JavaScript
 * Handles video upload, camera, and CCTV detection
 */

// API Base URL
const API_URL = '/api';

// State
let currentSessionId = null;
let userEmail = localStorage.getItem('alertEmail') || '';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Check if email is set
    checkEmailSetup();

    // Setup event listeners
    setupModeCards();
    setupModals();
    setupUpload();
    setupCamera();
    setupCctv();
    loadHistory();

    // Refresh history button
    document.getElementById('refreshHistory')?.addEventListener('click', loadHistory);
});

// ==================== Email Setup ====================

function checkEmailSetup() {
    const emailSection = document.getElementById('emailSection');
    const emailDisplay = document.getElementById('currentEmail');
    const emailInput = document.getElementById('alertEmail');

    if (userEmail) {
        if (emailDisplay) emailDisplay.textContent = userEmail;
        if (emailSection) emailSection.classList.add('email-set');
    }

    // Save email button
    document.getElementById('saveEmailBtn')?.addEventListener('click', saveEmail);

    // Edit email button
    document.getElementById('editEmailBtn')?.addEventListener('click', () => {
        const emailSection = document.getElementById('emailSection');
        emailSection?.classList.remove('email-set');
        document.getElementById('alertEmail').value = userEmail;
    });
}

function saveEmail() {
    const emailInput = document.getElementById('alertEmail');
    const email = emailInput?.value?.trim();

    if (!email || !isValidEmail(email)) {
        showToast('Please enter a valid email address', 'error');
        return;
    }

    userEmail = email;
    localStorage.setItem('alertEmail', email);

    // Update display
    document.getElementById('currentEmail').textContent = email;
    document.getElementById('emailSection')?.classList.add('email-set');

    showToast('Email saved! You will receive alerts at this address.', 'success');
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// ==================== Mode Cards ====================

function setupModeCards() {
    document.getElementById('uploadMode')?.addEventListener('click', () => {
        document.getElementById('uploadModal')?.classList.remove('hidden');
    });

    document.getElementById('cameraMode')?.addEventListener('click', () => {
        // Email is optional - detection works without it, just no alerts
        startCamera();
    });

    document.getElementById('cctvMode')?.addEventListener('click', () => {
        // Email is optional - detection works without it, just no alerts
        document.getElementById('cctvModal')?.classList.remove('hidden');
    });
}

// ==================== Modals ====================

function setupModals() {
    // Close buttons
    document.getElementById('closeUploadModal')?.addEventListener('click', () => {
        document.getElementById('uploadModal')?.classList.add('hidden');
        resetUpload();
    });

    document.getElementById('closeCameraModal')?.addEventListener('click', stopCamera);
    document.getElementById('closeCctvModal')?.addEventListener('click', () => {
        document.getElementById('cctvModal')?.classList.add('hidden');
    });
    document.getElementById('closeCctvStreamModal')?.addEventListener('click', stopCctv);

    // Click outside to close (with proper cleanup for camera/CCTV)
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                // Stop active sessions when closing modals by clicking outside
                if (modal.id === 'cameraModal') {
                    stopCamera();
                } else if (modal.id === 'cctvStreamModal') {
                    stopCctv();
                } else {
                    modal.classList.add('hidden');
                }
            }
        });
    });

    // Handle Escape key to close modals properly
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const cameraModal = document.getElementById('cameraModal');
            const cctvStreamModal = document.getElementById('cctvStreamModal');
            
            if (cameraModal && !cameraModal.classList.contains('hidden')) {
                stopCamera();
            } else if (cctvStreamModal && !cctvStreamModal.classList.contains('hidden')) {
                stopCctv();
            }
        }
    });
}

// ==================== Video Upload ====================

function setupUpload() {
    const uploadZone = document.getElementById('uploadZone');
    const videoInput = document.getElementById('videoInput');
    const selectFileBtn = document.getElementById('selectFileBtn');

    // Select file button
    selectFileBtn?.addEventListener('click', () => {
        videoInput?.click();
    });

    // File input change
    videoInput?.addEventListener('change', (e) => {
        if (e.target.files?.length) {
            handleVideoUpload(e.target.files[0]);
        }
    });

    // Drag and drop
    uploadZone?.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone?.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone?.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');

        if (e.dataTransfer.files?.length) {
            handleVideoUpload(e.dataTransfer.files[0]);
        }
    });

    // New upload button
    document.getElementById('newUploadBtn')?.addEventListener('click', resetUpload);
}

async function handleVideoUpload(file) {
    if (!file.type.startsWith('video/')) {
        showToast('Please select a video file', 'error');
        return;
    }

    // Show progress
    document.getElementById('uploadZone')?.classList.add('hidden');
    document.getElementById('uploadProgress')?.classList.remove('hidden');

    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    try {
        // Create form data
        const formData = new FormData();
        formData.append('video', file);
        formData.append('email', userEmail);

        // Simulate progress (actual progress would need XHR)
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            progressFill.style.width = `${progress}%`;
            progressText.textContent = `Processing... ${Math.round(progress)}%`;
        }, 500);

        // Upload
        const response = await fetch(`${API_URL}/detect/upload`, {
            method: 'POST',
            body: formData
        });

        clearInterval(progressInterval);
        progressFill.style.width = '100%';

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Upload failed');
        }

        const result = await response.json();
        showUploadResult(result);
        loadHistory();

    } catch (error) {
        console.error('Upload error:', error);
        showToast(error.message || 'Upload failed', 'error');
        resetUpload();
    }
}

function showUploadResult(result) {
    document.getElementById('uploadProgress')?.classList.add('hidden');
    document.getElementById('uploadResult')?.classList.remove('hidden');

    const statusEl = document.getElementById('resultStatus');
    const scoreEl = document.getElementById('resultScore');
    const downloadBtn = document.getElementById('downloadBtn');
    const previewVideo = document.getElementById('previewVideo');

    if (result.is_anomaly) {
        statusEl.textContent = 'ANOMALY DETECTED';
        statusEl.className = 'result-status anomaly';
    } else {
        statusEl.textContent = 'NORMAL';
        statusEl.className = 'result-status normal';
    }

    scoreEl.textContent = `Confidence: ${(result.combined_score * 100).toFixed(1)}%`;

    // Set video preview
    if (previewVideo && result.preview_url) {
        previewVideo.src = result.preview_url;
        previewVideo.load();
    }

    // Download button
    downloadBtn.onclick = () => {
        window.open(result.download_url, '_blank');
    };

    if (result.email_sent) {
        showToast('Alert email sent with video clip!', 'success');
    }
}

function resetUpload() {
    document.getElementById('uploadZone')?.classList.remove('hidden');
    document.getElementById('uploadProgress')?.classList.add('hidden');
    document.getElementById('uploadResult')?.classList.add('hidden');
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('videoInput').value = '';

    // Clear video preview
    const previewVideo = document.getElementById('previewVideo');
    if (previewVideo) {
        previewVideo.pause();
        previewVideo.src = '';
    }
}

// ==================== Camera Detection ====================

function setupCamera() {
    document.getElementById('stopCameraBtn')?.addEventListener('click', stopCamera);
}

async function startCamera() {
    try {
        const response = await fetch(`${API_URL}/detect/start-camera`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: userEmail })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to start camera');
        }

        const result = await response.json();
        currentSessionId = result.session_id;

        // Show modal and start stream
        document.getElementById('cameraModal')?.classList.remove('hidden');
        const streamImg = document.getElementById('cameraStream');
        streamImg.src = result.stream_url;

        showToast('Camera detection started', 'success');

    } catch (error) {
        console.error('Camera error:', error);
        showToast(error.message || 'Failed to start camera', 'error');
    }
}

async function stopCamera() {
    try {
        await fetch(`${API_URL}/detect/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: userEmail })
        });
    } catch (error) {
        console.error('Stop camera error:', error);
    }

    document.getElementById('cameraModal')?.classList.add('hidden');
    document.getElementById('cameraStream').src = '';
    currentSessionId = null;
    loadHistory();
}

// ==================== CCTV Detection ====================

function setupCctv() {
    document.getElementById('connectCctvBtn')?.addEventListener('click', startCctv);
    document.getElementById('stopCctvBtn')?.addEventListener('click', stopCctv);
}

async function startCctv() {
    const cctvUrl = document.getElementById('cctvUrl')?.value?.trim();

    if (!cctvUrl) {
        showToast('Please enter a CCTV stream URL', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/detect/start-cctv`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: cctvUrl, email: userEmail })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to connect to CCTV');
        }

        const result = await response.json();
        currentSessionId = result.session_id;

        // Hide connect modal, show stream modal
        document.getElementById('cctvModal')?.classList.add('hidden');
        document.getElementById('cctvStreamModal')?.classList.remove('hidden');

        const streamImg = document.getElementById('cctvStream');
        streamImg.src = result.stream_url;

        showToast('CCTV detection started', 'success');

    } catch (error) {
        console.error('CCTV error:', error);
        showToast(error.message || 'Failed to connect to CCTV', 'error');
    }
}

async function stopCctv() {
    try {
        await fetch(`${API_URL}/detect/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: userEmail })
        });
    } catch (error) {
        console.error('Stop CCTV error:', error);
    }

    document.getElementById('cctvStreamModal')?.classList.add('hidden');
    document.getElementById('cctvStream').src = '';
    currentSessionId = null;
    loadHistory();
}

// ==================== History ====================

async function loadHistory() {
    try {
        const response = await fetch(`${API_URL}/detect/logs?email=${encodeURIComponent(userEmail)}`);

        if (!response.ok) {
            throw new Error('Failed to load history');
        }

        const data = await response.json();
        renderHistory(data.logs || []);

    } catch (error) {
        console.error('Load history error:', error);
    }
}

function renderHistory(logs) {
    const tbody = document.getElementById('historyBody');
    if (!tbody) return;

    if (logs.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="5">No detection history yet</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = logs.map(log => {
        const date = new Date(log.timestamp);
        const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();

        const statusClass = log.anomaly_type === 'normal' ? 'normal' : 'anomaly';
        const statusText = log.anomaly_type === 'normal' ? 'Normal' : 'Anomaly';

        const sourceIcon = {
            'upload': '📁',
            'camera': '📹',
            'cctv': '📡'
        }[log.source_type] || '📁';

        return `
            <tr>
                <td>${dateStr}</td>
                <td>${sourceIcon} ${log.source_type}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>${(log.confidence_score * 100).toFixed(1)}%</td>
                <td>${log.email_sent ? '✅ Yes' : '❌ No'}</td>
            </tr>
        `;
    }).join('');
}

// ==================== Toast ====================

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 4000);
}
