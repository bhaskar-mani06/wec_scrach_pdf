// DOM elements
const urlInput = document.getElementById('urlInput');
const fetchBtn = document.getElementById('fetchBtn');
const websiteText = document.getElementById('websiteText');
const fileInput = document.getElementById('fileInput');
const fileLabel = document.getElementById('fileLabel');
const fileText = document.getElementById('fileText');
const compareBtn = document.getElementById('compareBtn');
const results = document.getElementById('results');
const diffContent = document.getElementById('diffContent');

// State
let websiteContent = '';
let fileContent = '';

// URL input event listener
urlInput.addEventListener('input', () => {
    updateCompareButton();
});

// Fetch website content
fetchBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim();
    if (!url) {
        showError(websiteText, 'Please enter a valid URL');
        return;
    }

    fetchBtn.disabled = true;
    fetchBtn.innerHTML = '<span class="loading"></span>Extracting...';
    
    try {
        const response = await fetch('/extract_text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();
        
        if (data.success) {
            websiteContent = data.text;
            websiteText.textContent = websiteContent;
            // Clear any previous highlights
            clearHighlights(websiteText);
            showSuccess(websiteText, data.message);
        } else {
            showError(websiteText, data.error);
        }
    } catch (error) {
        console.error('Error fetching website:', error);
        showError(websiteText, 'Failed to fetch website content. Please check the URL and try again.');
    } finally {
        fetchBtn.disabled = false;
        fetchBtn.innerHTML = 'Extract Text';
        updateCompareButton();
    }
});

// File upload handling
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'text/plain') {
        const formData = new FormData();
        formData.append('file', file);

        fetch('/upload_file', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                fileContent = data.text;
                fileText.textContent = fileContent;
                // Clear any previous highlights
                clearHighlights(fileText);
                fileLabel.innerHTML = `
                    <div class="file-icon">✅</div>
                    <div>${data.filename}</div>
                    <div style="font-size: 0.9rem; color: #6c757d; margin-top: 5px;">File loaded successfully</div>
                `;
                showSuccess(fileText, data.message);
            } else {
                showError(fileText, data.error);
            }
            updateCompareButton();
        })
        .catch(error => {
            console.error('Error uploading file:', error);
            showError(fileText, 'Failed to upload file. Please try again.');
        });
    } else {
        showError(fileText, 'Please select a valid .txt file');
    }
});

// Drag and drop functionality
fileLabel.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileLabel.classList.add('dragover');
});

fileLabel.addEventListener('dragleave', () => {
    fileLabel.classList.remove('dragover');
});

fileLabel.addEventListener('drop', (e) => {
    e.preventDefault();
    fileLabel.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];
        if (file.type === 'text/plain') {
            fileInput.files = files;
            fileInput.dispatchEvent(new Event('change'));
        } else {
            showError(fileText, 'Please drop a valid .txt file');
        }
    }
});

// Compare functionality
compareBtn.addEventListener('click', async () => {
    if (!websiteContent || !fileContent) {
        showError(diffContent, 'Please extract website content and upload a text file first.');
        return;
    }

    compareBtn.disabled = true;
    compareBtn.innerHTML = '<span class="loading"></span>Comparing...';

    try {
        const response = await fetch('/compare_texts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                text1: websiteContent, 
                text2: fileContent 
            })
        });

        const data = await response.json();
        
        if (response.ok) {
            displayDifferences(data);
        } else {
            showError(diffContent, data.error);
        }
    } catch (error) {
        console.error('Error comparing texts:', error);
        showError(diffContent, 'Failed to compare texts. Please try again.');
    } finally {
        compareBtn.disabled = false;
        compareBtn.innerHTML = 'Find Difference';
    }
});

// Helper functions
function updateCompareButton() {
    // Enable button only when both website content and file content are available
    compareBtn.disabled = !(websiteContent && fileContent);
}

function showError(element, message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = message;
    element.appendChild(errorDiv);
    
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

function showSuccess(element, message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success';
    successDiv.textContent = message;
    element.appendChild(successDiv);
    
    setTimeout(() => {
        successDiv.remove();
    }, 3000);
}

function displayDifferences(data) {
    // Show results with smooth slide down animation
    results.style.display = 'block';
    results.style.opacity = '0';
    results.style.transform = 'translateY(-20px)';
    
    // Animate slide down
    setTimeout(() => {
        results.style.transition = 'all 0.5s ease-in-out';
        results.style.opacity = '1';
        results.style.transform = 'translateY(0)';
    }, 100);
    
    // Scroll to results section
    setTimeout(() => {
        results.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }, 200);
    
    if (data.identical) {
        diffContent.innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <div style="font-size: 3rem; margin-bottom: 20px;">✅</div>
                <div style="color: #28a745; font-weight: bold; font-size: 1.2rem; margin-bottom: 10px;">Perfect Match!</div>
                <div style="color: #6c757d;">No differences found! The texts are identical.</div>
            </div>
        `;
        return;
    }
    
    let html = `
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 2.5rem; margin-bottom: 15px;">❌</div>
            <div style="color: #dc3545; font-weight: bold; font-size: 1.3rem; margin-bottom: 10px;">Found ${data.total_differences} difference(s)</div>
            <div style="color: #6c757d;">Below are the detailed differences between website content and file content:</div>
        </div>
    `;
    
    data.simple_diffs.forEach((diff, index) => {
        html += `
            <div style="margin-bottom: 20px; padding: 15px; border-radius: 10px; background: linear-gradient(145deg, #fff3cd 0%, #ffeaa7 100%); border-left: 5px solid #ffc107; box-shadow: 0 4px 15px rgba(255, 193, 7, 0.2);">
                <div style="font-weight: bold; color: #856404; margin-bottom: 10px; font-size: 1.1rem;">
                    📍 Difference #${index + 1} - Line ${diff.line_number}
                </div>
        `;
        
        if (diff.type === 'added') {
            html += `<div style="color: #28a745; background: rgba(40, 167, 69, 0.1); padding: 8px; border-radius: 5px; margin: 5px 0;">
                <strong>+ Added in file:</strong> <span class="highlight-added">${diff.file || '(empty line)'}</span>
            </div>`;
        } else if (diff.type === 'removed') {
            html += `<div style="color: #dc3545; background: rgba(220, 53, 69, 0.1); padding: 8px; border-radius: 5px; margin: 5px 0;">
                <strong>- Removed from website:</strong> <span class="highlight-removed">${diff.website || '(empty line)'}</span>
            </div>`;
        } else {
            html += `
                <div style="color: #dc3545; background: rgba(220, 53, 69, 0.1); padding: 8px; border-radius: 5px; margin: 5px 0;">
                    <strong>- Website content:</strong> <span class="highlight-removed">${diff.website || '(empty line)'}</span>
                </div>
                <div style="color: #28a745; background: rgba(40, 167, 69, 0.1); padding: 8px; border-radius: 5px; margin: 5px 0;">
                    <strong>+ File content:</strong> <span class="highlight-added">${diff.file || '(empty line)'}</span>
                </div>
            `;
        }
        
        html += `</div>`;
    });
    
    // Add highlighting to the text displays
    highlightDifferencesInText(data.simple_diffs);
    
    // Add summary at the end
    html += `
        <div style="margin-top: 30px; padding: 20px; background: linear-gradient(145deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 10px; border-left: 5px solid #2196f3;">
            <div style="font-weight: bold; color: #1976d2; margin-bottom: 10px;">📊 Summary</div>
            <div style="color: #424242;">
                • Total differences: <strong>${data.total_differences}</strong><br>
                • Comparison completed successfully<br>
                • Review the differences above to understand the changes
            </div>
        </div>
    `;
    
    diffContent.innerHTML = html;
}

// Function to highlight differences in the text display areas
function highlightDifferencesInText(differences) {
    const websiteText = document.getElementById('websiteText');
    const fileText = document.getElementById('fileText');
    
    if (!websiteText || !fileText) return;
    
    // Clear previous highlights
    clearHighlights(websiteText);
    clearHighlights(fileText);
    
    // Get the text content
    const websiteContent = websiteText.textContent;
    const fileContent = fileText.textContent;
    
    // Create highlighted versions
    let highlightedWebsite = websiteContent;
    let highlightedFile = fileContent;
    
    differences.forEach(diff => {
        if (diff.website && diff.website.trim()) {
            const escapedWebsite = escapeRegExp(diff.website);
            const highlightWebsite = `<span class="highlight-removed">${diff.website}</span>`;
            highlightedWebsite = highlightedWebsite.replace(new RegExp(escapedWebsite, 'g'), highlightWebsite);
        }
        
        if (diff.file && diff.file.trim()) {
            const escapedFile = escapeRegExp(diff.file);
            const highlightFile = `<span class="highlight-added">${diff.file}</span>`;
            highlightedFile = highlightedFile.replace(new RegExp(escapedFile, 'g'), highlightFile);
        }
    });
    
    // Update the text displays with highlighted content
    websiteText.innerHTML = highlightedWebsite;
    fileText.innerHTML = highlightedFile;
}

// Function to clear previous highlights
function clearHighlights(element) {
    const highlights = element.querySelectorAll('.highlight-added, .highlight-removed');
    highlights.forEach(highlight => {
        const parent = highlight.parentNode;
        parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
        parent.normalize();
    });
}

// Function to escape special regex characters
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
