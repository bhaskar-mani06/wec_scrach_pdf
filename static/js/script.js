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
            // Display the content in the text area like in the image
            websiteText.innerHTML = `<div class="content-preview">${websiteContent}</div>`;
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
                // Display the content in the text area like in the image
                fileText.innerHTML = `<div class="content-preview">${fileContent}</div>`;
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
    
    // Create simple layout like the image shows
    let html = `
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 2.5rem; margin-bottom: 15px;">📊</div>
            <div style="color: #dc3545; font-weight: bold; font-size: 1.3rem; margin-bottom: 10px;">Found ${data.total_differences} difference(s)</div>
            <div style="color: #6c757d;">Side-by-side comparison highlighting the differences:</div>
        </div>
        
        <div class="diff-container">
            <div class="diff-header">
                <div class="diff-header-left">
                    <span class="diff-label removed">${data.simple_diffs.filter(d => d.type === 'removed').length} removals</span>
                    <span class="diff-lines">${websiteContent.split('\n').length} lines</span>
                    <button class="copy-btn" onclick="copyToClipboard('website')">Copy</button>
                </div>
                <div class="diff-header-right">
                    <span class="diff-label added">${data.simple_diffs.filter(d => d.type === 'added').length} additions</span>
                    <span class="diff-lines">${fileContent.split('\n').length} lines</span>
                    <button class="copy-btn" onclick="copyToClipboard('file')">Copy</button>
                </div>
            </div>
            
            <div class="diff-content-wrapper">
                <div class="diff-left">
                    <div class="diff-line-numbers">
                        ${generateLineNumbers(websiteContent)}
                    </div>
                    <div class="diff-text-content" id="diffWebsiteContent">
                        ${formatDiffContent(websiteContent, data.simple_diffs, 'website')}
                    </div>
                </div>
                
                <div class="diff-right">
                    <div class="diff-line-numbers">
                        ${generateLineNumbers(fileContent)}
                    </div>
                    <div class="diff-text-content" id="diffFileContent">
                        ${formatDiffContent(fileContent, data.simple_diffs, 'file')}
                    </div>
                </div>
            </div>
        </div>
        
        <div style="margin-top: 30px; padding: 20px; background: linear-gradient(145deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 10px; border-left: 5px solid #2196f3;">
            <div style="font-weight: bold; color: #1976d2; margin-bottom: 10px;">📊 Summary</div>
            <div style="color: #424242;">
                • Total differences: <strong>${data.total_differences}</strong><br>
                • Website lines: <strong>${websiteContent.split('\n').length}</strong><br>
                • File lines: <strong>${fileContent.split('\n').length}</strong><br>
                • Comparison completed successfully
            </div>
        </div>
    `;
    
    diffContent.innerHTML = html;
}

// Helper function to format extracted content for display (editable)
function formatExtractedContent(content, type) {
    const lines = content.split('\n');
    return lines.map((line, index) => {
        const lineNumber = (index + 1).toString().padStart(3, ' ');
        const lineContent = line || '';
        return `<div class="extracted-line" data-line="${index}">
            <span class="extracted-line-number">${lineNumber}</span>
            <input type="text" class="extracted-line-input" value="${escapeHtml(lineContent)}" data-type="${type}" data-line="${index}" />
        </div>`;
    }).join('');
}

// Helper function to generate line numbers
function generateLineNumbers(content) {
    const lines = content.split('\n');
    return lines.map((_, index) => `<div class="line-number">${index + 1}</div>`).join('');
}

// Helper function to format diff content with highlighting
function formatDiffContent(content, differences, type) {
    const lines = content.split('\n');
    let formattedLines = [];
    
    lines.forEach((line, index) => {
        let lineClass = 'diff-line';
        let lineContent = line || '&nbsp;'; // Handle empty lines
        
        // Check if this line has differences
        const hasDiff = differences.some(diff => {
            if (type === 'website' && diff.website) {
                return line.toLowerCase().trim() === diff.website.toLowerCase().trim();
            } else if (type === 'file' && diff.file) {
                return line.toLowerCase().trim() === diff.file.toLowerCase().trim();
            }
            return false;
        });
        
        if (hasDiff) {
            if (type === 'website') {
                lineClass += ' diff-removed';
            } else {
                lineClass += ' diff-added';
            }
        }
        
        formattedLines.push(`<div class="${lineClass}">${escapeHtml(lineContent)}</div>`);
    });
    
    return formattedLines.join('');
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Copy to clipboard function
function copyToClipboard(type) {
    const content = type === 'website' ? websiteContent : fileContent;
    navigator.clipboard.writeText(content).then(() => {
        // Show success feedback
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.style.background = '#28a745';
        
        setTimeout(() => {
            button.textContent = originalText;
            button.style.background = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
}

// Function to get edited content from inputs
function getEditedContent(type) {
    const inputs = document.querySelectorAll(`input[data-type="${type}"]`);
    return Array.from(inputs).map(input => input.value).join('\n');
}

// Function to compare edited texts
async function compareEditedTexts() {
    const editedWebsiteContent = getEditedContent('website');
    const editedFileContent = getEditedContent('file');
    
    if (!editedWebsiteContent || !editedFileContent) {
        alert('Please make sure both texts have content to compare.');
        return;
    }
    
    const compareBtn = document.getElementById('compareEditedBtn');
    compareBtn.disabled = true;
    compareBtn.innerHTML = '<span class="loading"></span>Comparing...';
    
    try {
        const response = await fetch('/compare_texts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                text1: editedWebsiteContent, 
                text2: editedFileContent 
            })
        });

        const data = await response.json();
        
        if (response.ok) {
            displayEditedComparison(data, editedWebsiteContent, editedFileContent);
        } else {
            alert('Error comparing texts: ' + data.error);
        }
    } catch (error) {
        console.error('Error comparing texts:', error);
        alert('Failed to compare texts. Please try again.');
    } finally {
        compareBtn.disabled = false;
        compareBtn.innerHTML = '🔄 Compare Edited Texts';
    }
}

// Function to display comparison results for edited texts
function displayEditedComparison(data, editedWebsiteContent, editedFileContent) {
    const comparisonResults = document.getElementById('comparisonResults');
    comparisonResults.style.display = 'block';
    
    if (data.identical) {
        comparisonResults.innerHTML = `
            <h4 style="color: #2d3748; margin: 40px 0 20px 0; font-size: 1.3rem; display: flex; align-items: center; gap: 10px;">
                🔍 Comparison Results
            </h4>
            <div style="text-align: center; padding: 40px;">
                <div style="font-size: 3rem; margin-bottom: 20px;">✅</div>
                <div style="color: #28a745; font-weight: bold; font-size: 1.2rem; margin-bottom: 10px;">Perfect Match!</div>
                <div style="color: #6c757d;">No differences found! The edited texts are identical.</div>
            </div>
        `;
        return;
    }
    
    // Create comparison display for edited texts
    let html = `
        <h4 style="color: #2d3748; margin: 40px 0 20px 0; font-size: 1.3rem; display: flex; align-items: center; gap: 10px;">
            🔍 Comparison Results
        </h4>
        
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="font-size: 2.5rem; margin-bottom: 15px;">📊</div>
            <div style="color: #dc3545; font-weight: bold; font-size: 1.3rem; margin-bottom: 10px;">Found ${data.total_differences} difference(s)</div>
            <div style="color: #6c757d;">Side-by-side comparison highlighting the differences:</div>
        </div>
        
        <div class="diff-container">
            <div class="diff-header">
                <div class="diff-header-left">
                    <span class="diff-label removed">${data.simple_diffs.filter(d => d.type === 'removed').length} removals</span>
                    <span class="diff-lines">${editedWebsiteContent.split('\n').length} lines</span>
                    <button class="copy-btn" onclick="copyEditedToClipboard('website')">Copy</button>
                </div>
                <div class="diff-header-right">
                    <span class="diff-label added">${data.simple_diffs.filter(d => d.type === 'added').length} additions</span>
                    <span class="diff-lines">${editedFileContent.split('\n').length} lines</span>
                    <button class="copy-btn" onclick="copyEditedToClipboard('file')">Copy</button>
                </div>
            </div>
            
            <div class="diff-content-wrapper">
                <div class="diff-left">
                    <div class="diff-line-numbers">
                        ${generateLineNumbers(editedWebsiteContent)}
                    </div>
                    <div class="diff-text-content" id="diffWebsiteContent">
                        ${formatDiffContent(editedWebsiteContent, data.simple_diffs, 'website')}
                    </div>
                </div>
                
                <div class="diff-right">
                    <div class="diff-line-numbers">
                        ${generateLineNumbers(editedFileContent)}
                    </div>
                    <div class="diff-text-content" id="diffFileContent">
                        ${formatDiffContent(editedFileContent, data.simple_diffs, 'file')}
                    </div>
                </div>
            </div>
        </div>
        
        <div style="margin-top: 30px; padding: 20px; background: linear-gradient(145deg, #e3f2fd 0%, #bbdefb 100%); border-radius: 10px; border-left: 5px solid #2196f3;">
            <div style="font-weight: bold; color: #1976d2; margin-bottom: 10px;">📊 Summary</div>
            <div style="color: #424242;">
                • Total differences: <strong>${data.total_differences}</strong><br>
                • Website lines: <strong>${editedWebsiteContent.split('\n').length}</strong><br>
                • File lines: <strong>${editedFileContent.split('\n').length}</strong><br>
                • Comparison completed successfully
            </div>
        </div>
    `;
    
    comparisonResults.innerHTML = html;
    
    // Scroll to comparison results
    setTimeout(() => {
        comparisonResults.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }, 100);
}

// Function to copy edited content to clipboard
function copyEditedToClipboard(type) {
    const content = getEditedContent(type);
    navigator.clipboard.writeText(content).then(() => {
        // Show success feedback
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = 'Copied!';
        button.style.background = '#28a745';
        
        setTimeout(() => {
            button.textContent = originalText;
            button.style.background = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
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
