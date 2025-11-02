// DOM Elements
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const controls = document.getElementById('controls');
const resultsSection = document.getElementById('resultsSection');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const errorMessage = document.getElementById('errorMessage');

// Control elements
const adaptiveCheck = document.getElementById('adaptiveCheck');
const manualControls = document.getElementById('manualControls');
const lowerThreshold = document.getElementById('lowerThreshold');
const upperThreshold = document.getElementById('upperThreshold');
const blurKernel = document.getElementById('blurKernel');
const lowerValue = document.getElementById('lowerValue');
const upperValue = document.getElementById('upperValue');
const blurValue = document.getElementById('blurValue');
const processBtn = document.getElementById('processBtn');

// Result elements
const originalImg = document.getElementById('originalImg');
const grayscaleImg = document.getElementById('grayscaleImg');
const blurredImg = document.getElementById('blurredImg');
const edgesImg = document.getElementById('edgesImg');
const imageSize = document.getElementById('imageSize');
const thresholdInfo = document.getElementById('thresholdInfo');
const downloadBtn = document.getElementById('downloadBtn');

let currentFile = null;
let currentEdgesData = null;

// File input change
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

// Drag and drop
uploadBox.addEventListener('click', () => fileInput.click());

uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('dragover');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('dragover');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
        handleFile(e.dataTransfer.files[0]);
    }
});

// Handle file selection
function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        showError('Please select a valid image file.');
        return;
    }
    
    if (file.size > 16 * 1024 * 1024) {
        showError('File size exceeds 16MB limit.');
        return;
    }
    
    currentFile = file;
    controls.style.display = 'block';
    resultsSection.style.display = 'none';
    hideError();
    
    // Show file name
    uploadBox.innerHTML = `
        <div class="upload-icon">✅</div>
        <h3>${file.name}</h3>
        <p>File selected. Adjust parameters and click "Process Image"</p>
        <label for="fileInput" class="btn-primary" style="margin-top: 15px;">Change File</label>
    `;
}

// Adaptive checkbox change
adaptiveCheck.addEventListener('change', () => {
    if (adaptiveCheck.checked) {
        manualControls.style.display = 'none';
    } else {
        manualControls.style.display = 'block';
    }
});

// Update slider values display
lowerThreshold.addEventListener('input', () => {
    lowerValue.textContent = lowerThreshold.value;
});

upperThreshold.addEventListener('input', () => {
    upperValue.textContent = upperThreshold.value;
});

blurKernel.addEventListener('input', () => {
    blurValue.textContent = blurKernel.value;
});

// Process image
processBtn.addEventListener('click', async () => {
    if (!currentFile) {
        showError('Please select an image first.');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', currentFile);
    formData.append('adaptive', adaptiveCheck.checked);
    
    if (!adaptiveCheck.checked) {
        formData.append('lower_threshold', lowerThreshold.value);
        formData.append('upper_threshold', upperThreshold.value);
    }
    
    formData.append('blur_kernel', blurKernel.value);
    
    loading.style.display = 'block';
    resultsSection.style.display = 'none';
    hideError();
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to process image');
        }
        
        // Display results
        originalImg.src = data.original;
        grayscaleImg.src = data.grayscale;
        blurredImg.src = data.blurred;
        edgesImg.src = data.edges;
        
        imageSize.textContent = `Size: ${data.image_size}`;
        thresholdInfo.textContent = `Thresholds: Lower=${data.thresholds.lower}, Upper=${data.thresholds.upper}`;
        
        currentEdgesData = data.edges;
        
        resultsSection.style.display = 'grid';
        loading.style.display = 'none';
        
        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
    } catch (err) {
        loading.style.display = 'none';
        showError(err.message);
    }
});

// Download result
downloadBtn.addEventListener('click', async () => {
    if (!currentEdgesData) {
        showError('No processed image available.');
        return;
    }
    
    try {
        const response = await fetch('/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image_data: currentEdgesData
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to download image');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'edge_detected.jpg';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
    } catch (err) {
        showError('Failed to download image: ' + err.message);
    }
});

// Utility functions
function showError(message) {
    errorMessage.textContent = message;
    error.style.display = 'block';
}

function hideError() {
    error.style.display = 'none';
}

