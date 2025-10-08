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
    
    // Validate content lengths
    if (websiteContent.length < 10) {
        showError(diffContent, 'Website content is too short. Please extract content first.');
        return;
    }
    
    if (fileContent.length < 10) {
        showError(diffContent, 'File content is too short. Please upload a valid file.');
        return;
    }

    compareBtn.disabled = true;
    compareBtn.innerHTML = '<span class="loading"></span>Comparing...';

    try {
        console.log('=== SENDING COMPARISON REQUEST ===');
        console.log('Website content length:', websiteContent.length);
        console.log('File content length:', fileContent.length);
        
        const requestData = { 
            text1: websiteContent, 
            text2: fileContent 
        };
        
        console.log('Request data:', requestData);
        
        const response = await fetch('/compare_texts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);
        
        if (!response.ok) {
            console.error('HTTP Error:', response.status, response.statusText);
            const errorText = await response.text();
            console.error('Error response:', errorText);
            showError(diffContent, `Server error: ${response.status} - ${response.statusText}`);
            return;
        }

        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.error) {
            console.error('Server error:', data.error);
            showError(diffContent, data.error);
        } else {
            displayDifferences(data);
        }
    } catch (error) {
        console.error('Error comparing texts:', error);
        console.error('Error details:', error.message, error.stack);
        showError(diffContent, `Failed to compare texts: ${error.message}`);
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
        // Even for identical texts, show side-by-side comparison like Diffchecker
        diffContent.innerHTML = `
            <div class="diff-container">
                <div class="diff-header">
                    <div class="diff-header-left">
                        <span class="diff-label" style="background: #ffebee; color: #c62828; border: 1px solid #ef5350;">🌐 WEBSITE CONTENT</span>
                    </div>
                    <div class="diff-header-right">
                        <span class="diff-label" style="background: #e8f5e8; color: #2e7d32; border: 1px solid #4caf50;">📄 TEXT FILE</span>
                    </div>
                </div>
                
                <div class="diff-content-wrapper">
                    <div class="diff-left">
                        <div class="diff-text-content" id="diffWebsiteContent">
                            ${generateContentWithInlineLineNumbers(websiteContent, fileContent, [], null).left}
                        </div>
                    </div>
                    
                    <div class="diff-right">
                        <div class="diff-text-content" id="diffFileContent">
                            ${generateContentWithInlineLineNumbers(websiteContent, fileContent, [], null).right}
                        </div>
                    </div>
                </div>
            </div>
        `;
        return;
    }
    
    // Debug: Log differences to console
    console.log('Full data received:', data);
    console.log('Differences found:', data.simple_diffs);
    console.log('Total differences:', data.total_differences);
    
    // Check if simple_diffs exists and is an array
    if (!data.simple_diffs || !Array.isArray(data.simple_diffs)) {
        console.error('simple_diffs is not an array:', data.simple_diffs);
        showError(diffContent, 'Error: Invalid data format received from server');
        return;
    }
    
    console.log('Removed items:', data.simple_diffs.filter(d => d.type === 'removed'));
    console.log('Added items:', data.simple_diffs.filter(d => d.type === 'added'));
    
    // Force highlight first few differences for testing
    if (data.simple_diffs.length > 0) {
        console.log('First removed item:', data.simple_diffs.find(d => d.type === 'removed'));
        console.log('First added item:', data.simple_diffs.find(d => d.type === 'added'));
    }
    
    // Create layout like Diffchecker with proper highlighting and view options
    let html = `
        <div class="diff-container">
            <div class="diff-header">
                <div class="diff-header-left">
                    <span class="diff-label" style="background: #ffebee; color: #c62828; border: 1px solid #ef5350;">🌐 WEBSITE CONTENT</span>
                </div>
                <div class="diff-header-right">
                    <span class="diff-label" style="background: #e8f5e8; color: #2e7d32; border: 1px solid #4caf50;">📄 TEXT FILE</span>
                </div>
            </div>
            
            <div class="diff-content-wrapper">
                <div class="diff-left">
                    <div class="diff-text-content" id="diffWebsiteContent">
                        ${generateContentWithInlineLineNumbers(websiteContent, fileContent, data.simple_diffs, data).left}
                    </div>
                </div>
                
                <div class="diff-right">
                    <div class="diff-text-content" id="diffFileContent">
                        ${generateContentWithInlineLineNumbers(websiteContent, fileContent, data.simple_diffs, data).right}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    diffContent.innerHTML = html;
    
    // Ensure independent scrolling by removing any potential synchronization
    setTimeout(() => {
        const leftPanel = document.getElementById('diffWebsiteContent');
        const rightPanel = document.getElementById('diffFileContent');
        
        if (leftPanel && rightPanel) {
            // Remove any existing scroll event listeners
            leftPanel.removeEventListener('scroll', () => {});
            rightPanel.removeEventListener('scroll', () => {});
            
            // Ensure both panels have independent scrolling
            leftPanel.style.overflowY = 'auto';
            rightPanel.style.overflowY = 'auto';
            
            // Prevent any scroll synchronization
            leftPanel.addEventListener('scroll', (e) => {
                e.stopPropagation();
            });
            
            rightPanel.addEventListener('scroll', (e) => {
                e.stopPropagation();
            });
        }
    }, 100);
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

// Helper function to generate content with inline line numbers
function generateContentWithInlineLineNumbers(content1, content2, differences, data = null) {
    const lines1 = content1.split('\n');
    const lines2 = content2.split('\n');
    
    let result1 = '';
    let result2 = '';
    
    // Create a map of differences for faster lookup
    const removedDiffs = new Map();
    const addedDiffs = new Map();
    
    if (differences && Array.isArray(differences)) {
        differences.forEach(diff => {
            if (diff.type === 'removed' && diff.website) {
                const key = diff.website.toLowerCase().trim();
                removedDiffs.set(key, diff.website);
            } else if (diff.type === 'added' && diff.file) {
                const key = diff.file.toLowerCase().trim();
                addedDiffs.set(key, diff.file);
            }
        });
    }
    
    // Format content1 with inline line numbers
    lines1.forEach((line, index) => {
        const lineNum = index + 1;
        let lineClass = 'website-line';
        let lineContent = line || '';
        
        // Remove existing line numbers from website content (like "1. ", "2. ", etc.)
        lineContent = lineContent.replace(/^\d+\.\s*/, '');
        
        // Check if this line has differences
        let hasDiff = false;
        if (lineContent.trim()) {
            const lineKey = lineContent.toLowerCase().trim();
            if (removedDiffs.has(lineKey)) {
                hasDiff = true;
                lineClass += ' diff-highlight-removed';
            } else {
                // Check for partial matches
                for (const [key, value] of removedDiffs) {
                    if (lineKey.includes(key) || key.includes(lineKey)) {
                        hasDiff = true;
                        lineClass += ' diff-highlight-removed';
                        break;
                    }
                }
            }
        }
        
        result1 += `<div class="${lineClass}">
            <span class="inline-line-number">${lineNum}</span>
            <span class="inline-line-content">${escapeHtml(lineContent)}</span>
        </div>`;
    });
    
    // Format content2 with inline line numbers
    lines2.forEach((line, index) => {
        const lineNum = index + 1;
        let lineClass = 'website-line';
        let lineContent = line || '';
        
        // Remove existing line numbers from file content (like "1. ", "2. ", etc.)
        lineContent = lineContent.replace(/^\d+\.\s*/, '');
        
        // Check if this line has differences
        let hasDiff = false;
        if (lineContent.trim()) {
            const lineKey = lineContent.toLowerCase().trim();
            if (addedDiffs.has(lineKey)) {
                hasDiff = true;
                lineClass += ' diff-highlight-added';
            } else {
                // Check for partial matches
                for (const [key, value] of addedDiffs) {
                    if (lineKey.includes(key) || key.includes(lineKey)) {
                        hasDiff = true;
                        lineClass += ' diff-highlight-added';
                        break;
                    }
                }
            }
        }
        
        result2 += `<div class="${lineClass}">
            <span class="inline-line-number">${lineNum}</span>
            <span class="inline-line-content">${escapeHtml(lineContent)}</span>
        </div>`;
    });
    
    return { left: result1, right: result2 };
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

// Helper function to format website content with line numbers (non-scrollable)
function formatWebsiteContentWithLineNumbers(content) {
    const lines = content.split('\n');
    return lines.map((line, index) => {
        const lineContent = line || '&nbsp;'; // Handle empty lines
        return `<div class="website-line">${escapeHtml(lineContent)}</div>`;
    }).join('');
}

// Helper function to format content with highlighting for differences
function formatContentWithHighlighting(content, differences, type) {
    const lines = content.split('\n');
    return lines.map((line, index) => {
        let lineContent = line || '&nbsp;'; // Handle empty lines
        let lineClass = 'website-line';
        
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
                lineClass += ' diff-highlight-removed';
            } else {
                lineClass += ' diff-highlight-added';
            }
        }
        
        // Word-level highlighting is now handled by CSS classes only
        
        return `<div class="${lineClass}">${lineContent}</div>`;
    }).join('');
}

// Helper function to highlight different words within a line - Diffchecker style
function highlightDifferentWords(lineContent, differences, type) {
    if (!lineContent || !differences || differences.length === 0) {
        return escapeHtml(lineContent);
    }
    
    let highlightedContent = escapeHtml(lineContent);
    
    // Find matching differences for this line
    const matchingDiffs = differences.filter(diff => {
        if (type === 'removed' && diff.type === 'removed' && diff.website) {
            const diffText = diff.website.toLowerCase().trim();
            const lineText = lineContent.toLowerCase().trim();
            return lineText.includes(diffText) || diffText.includes(lineText);
        } else if (type === 'added' && diff.type === 'added' && diff.file) {
            const diffText = diff.file.toLowerCase().trim();
            const lineText = lineContent.toLowerCase().trim();
            return lineText.includes(diffText) || diffText.includes(lineText);
        }
        return false;
    });
    
    // If we found matching differences, apply word-level highlighting
    if (matchingDiffs.length > 0) {
        // Apply word-level highlighting like Diffchecker
        for (const diff of matchingDiffs) {
            const diffText = type === 'removed' ? diff.website : diff.file;
            if (diffText) {
                // Split into words and highlight each word
                const words = diffText.split(/\s+/);
                for (const word of words) {
                    if (word.length > 2) { // Only highlight words longer than 2 characters
                        const regex = new RegExp(`\\b${escapeRegExp(word)}\\b`, 'gi');
                        const highlightClass = type === 'removed' ? 'word-highlight-removed' : 'word-highlight-added';
                        highlightedContent = highlightedContent.replace(regex, `<span class="${highlightClass}">$&</span>`);
                    }
                }
            }
        }
    }
    
    return highlightedContent;
}

// Helper function to escape regex special characters
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Enhanced function to format independent content for diff view with better highlighting
function formatIndependentContent(content1, content2, differences, data = null) {
    // Validate inputs
    if (!content1 || !content2) {
        console.error('Invalid content provided to formatIndependentContent');
        return { left: '', right: '' };
    }
    
    if (!differences || !Array.isArray(differences)) {
        console.error('Invalid differences provided to formatIndependentContent:', differences);
        return { left: '', right: '' };
    }
    
    const lines1 = content1.split('\n');
    const lines2 = content2.split('\n');
    
    let result1 = '';
    let result2 = '';
    
    // Create a map of differences for faster lookup
    const removedDiffs = new Map();
    const addedDiffs = new Map();
    
    differences.forEach(diff => {
        if (diff.type === 'removed' && diff.website) {
            const key = diff.website.toLowerCase().trim();
            removedDiffs.set(key, diff.website);
        } else if (diff.type === 'added' && diff.file) {
            const key = diff.file.toLowerCase().trim();
            addedDiffs.set(key, diff.file);
        }
    });
    
    // Format left side (website content) - all lines independently
    lines1.forEach((line, index) => {
        let lineClass1 = 'website-line';
        let lineContent1 = line || '';
        
        // Check if this line has differences with improved matching
        let hasDiff1 = false;
        let matchedDiff1 = null;
        
        if (lineContent1.trim()) {
            const lineKey = lineContent1.toLowerCase().trim();
            
            // Check for exact match first
            if (removedDiffs.has(lineKey)) {
                hasDiff1 = true;
                matchedDiff1 = removedDiffs.get(lineKey);
            } else {
                // Check for partial matches
                for (const [key, value] of removedDiffs) {
                    if (lineKey.includes(key) || key.includes(lineKey)) {
                        hasDiff1 = true;
                        matchedDiff1 = value;
                        break;
                    }
                }
            }
        }
        
        if (hasDiff1) {
            lineClass1 += ' diff-highlight-removed';
            // Only add word-level highlighting if the line is significantly different
            if (matchedDiff1 && lineContent1.toLowerCase().trim() !== matchedDiff1.toLowerCase().trim()) {
                lineContent1 = highlightWordsInLine(lineContent1, matchedDiff1, 'removed');
            }
        }
        
        result1 += `<div class="${lineClass1}">${escapeHtml(lineContent1)}</div>`;
    });
    
    // Format right side (file content) - all lines independently
    lines2.forEach((line, index) => {
        let lineClass2 = 'website-line';
        let lineContent2 = line || '';
        
        // Check if this line has differences with improved matching
        let hasDiff2 = false;
        let matchedDiff2 = null;
        
        if (lineContent2.trim()) {
            const lineKey = lineContent2.toLowerCase().trim();
            
            // Check for exact match first
            if (addedDiffs.has(lineKey)) {
                hasDiff2 = true;
                matchedDiff2 = addedDiffs.get(lineKey);
            } else {
                // Check for partial matches
                for (const [key, value] of addedDiffs) {
                    if (lineKey.includes(key) || key.includes(lineKey)) {
                        hasDiff2 = true;
                        matchedDiff2 = value;
                        break;
                    }
                }
            }
        }
        
        if (hasDiff2) {
            lineClass2 += ' diff-highlight-added';
            // Only add word-level highlighting if the line is significantly different
            if (matchedDiff2 && lineContent2.toLowerCase().trim() !== matchedDiff2.toLowerCase().trim()) {
                lineContent2 = highlightWordsInLine(lineContent2, matchedDiff2, 'added');
            }
        }
        
        result2 += `<div class="${lineClass2}">${escapeHtml(lineContent2)}</div>`;
    });
    
    return { left: result1, right: result2 };
}

// Enhanced function to highlight words within a line - improved to highlight meaningful phrases
function highlightWordsInLine(lineContent, diffContent, type) {
    if (!lineContent || !diffContent) return escapeHtml(lineContent);
    
    // Instead of highlighting individual words, highlight the entire line or meaningful phrases
    // This prevents the cluttered individual word highlighting
    
    // Check if the line content is significantly different from diff content
    const lineWords = lineContent.toLowerCase().split(/\s+/).filter(w => w.length > 2);
    const diffWords = diffContent.toLowerCase().split(/\s+/).filter(w => w.length > 2);
    
    // Calculate similarity
    const commonWords = lineWords.filter(word => diffWords.includes(word));
    const similarity = commonWords.length / Math.max(lineWords.length, diffWords.length);
    
    // If similarity is low (less than 50%), highlight the entire line
    if (similarity < 0.5) {
        const highlightClass = type === 'removed' ? 'word-highlight-removed' : 'word-highlight-added';
        return `<span class="${highlightClass}">${escapeHtml(lineContent)}</span>`;
    }
    
    // If similarity is high, try to highlight only the different parts
    if (similarity >= 0.5) {
        // Find words that are different
        const differentWords = lineWords.filter(word => !diffWords.includes(word));
        
        if (differentWords.length > 0) {
            let highlightedContent = escapeHtml(lineContent);
            const highlightClass = type === 'removed' ? 'word-highlight-removed' : 'word-highlight-added';
            
            // Highlight only the different words
            differentWords.forEach(word => {
                const escapedWord = escapeRegExp(word);
                const regex = new RegExp(`\\b${escapedWord}\\b`, 'gi');
                highlightedContent = highlightedContent.replace(regex, `<span class="${highlightClass}">$&</span>`);
            });
            
            return highlightedContent;
        }
    }
    
    // If no significant differences, return escaped original content
    return escapeHtml(lineContent);
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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




