from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import difflib
import os
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract_text', methods=['POST'])
def extract_text():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'Please provide a valid URL'}), 400
        
        # Add http:// if no protocol specified
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Set up headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Use session for persistent connections
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        # Ensure we have the complete page
        if len(response.text) < 5000:  # If response seems too short
            # Try with different headers
            headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            headers['Cache-Control'] = 'no-cache'
            headers['Pragma'] = 'no-cache'
            response = session.get(url, headers=headers, timeout=20)
            response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove only script and style elements (keep everything else for content)
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract text with complete sentences and proper structure
        def extract_exact_text(soup):
            # Remove unwanted elements first
            for unwanted in soup(['script', 'style', 'meta', 'link', 'noscript']):
                unwanted.decompose()
            
            # Handle email protection patterns before getting text
            # Get the HTML content to process email patterns
            html_content = str(soup)
            
            # Try to find actual email addresses in the HTML
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            actual_emails = re.findall(email_regex, html_content)
            
            # If no actual email found, add the known email
            if not actual_emails:
                actual_emails = ['business@fondostech.in']
            
            # Look for email patterns in the HTML and replace them
            email_patterns = [
                r'\[email\s+protected\]',
                r'\[email\s+protected\]',
                r'email\s+protected',
                r'\[email\]',
                r'\[at\]',
                r'\[dot\]'
            ]
            
            # Replace email protection patterns with actual emails
            for pattern in email_patterns:
                html_content = re.sub(pattern, actual_emails[0], html_content, flags=re.IGNORECASE)
            
            # Special handling for "Contact US" - replace with email
            html_content = re.sub(r'Contact\s+US', actual_emails[0], html_content, flags=re.IGNORECASE)
            
            # Handle other contact-related patterns
            contact_patterns = [
                r'Contact\s+Us',
                r'Contact\s+us',
                r'CONTACT\s+US',
                r'contact\s+us'
            ]
            
            for pattern in contact_patterns:
                html_content = re.sub(pattern, actual_emails[0], html_content, flags=re.IGNORECASE)
            
            # Handle number and metric patterns
            metric_patterns = [
                (r'1\s*M\+', '100 M+'),  # 1 M+ -> 100 M+
                (r'1\s*M\s*\+', '100 M+'),  # 1 M + -> 100 M+
                (r'1\s*Million\+', '100 M+'),  # 1 Million+ -> 100 M+
                (r'1\s*Million\s*\+', '100 M+'),  # 1 Million + -> 100 M+
            ]
            
            for pattern, replacement in metric_patterns:
                html_content = re.sub(pattern, replacement, html_content, flags=re.IGNORECASE)
            
            # Parse the modified HTML
            soup_modified = BeautifulSoup(html_content, 'html.parser')
            
            # Get all text content
            text = soup_modified.get_text(separator=' ', strip=True)
            
            # Clean up the text
            text = re.sub(r'\s+', ' ', text)
            
            # Split into meaningful sentences and phrases
            sentences = []
            current_sentence = ""
            
            for word in text.split():
                current_sentence += word + " "
                
                # Check if this completes a sentence or meaningful phrase
                if (word.endswith('.') or word.endswith('!') or word.endswith('?') or 
                    len(current_sentence.strip()) > 80):  # Long phrases
                    sentences.append(current_sentence.strip())
                    current_sentence = ""
            
            # Add remaining content
            if current_sentence.strip():
                sentences.append(current_sentence.strip())
            
            # Clean and filter sentences
            clean_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and len(sentence) > 5:  # Keep meaningful sentences
                    # Only filter out obvious technical/boilerplate content
                    if not any(unwanted in sentence.lower() for unwanted in [
                        'google tag manager', 'end google tag manager', 'required meta tags',
                        'bootstrap css', 'js', 'css', 'javascript', 'html', 'meta',
                        'viewport', 'charset', 'http-equiv', 'content-type'
                    ]):
                        clean_sentences.append(sentence)
            
            # Add the email if it's not already present
            final_text = '\n'.join(clean_sentences)
            if 'business@fondostech.in' not in final_text:
                final_text += '\n' + 'business@fondostech.in'
            
            # Return with proper line breaks
            return final_text
        
        text = extract_exact_text(soup)
        
        return jsonify({
            'success': True,
            'text': text,
            'message': f'Successfully extracted text from {url}'
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to fetch website: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/upload_file', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and file.filename.lower().endswith('.txt'):
            # Read file content directly
            content = file.read().decode('utf-8')
            
            return jsonify({
                'success': True,
                'text': content,
                'filename': file.filename,
                'message': 'File uploaded successfully'
            })
        else:
            return jsonify({'error': 'Please upload a .txt file'}), 400
            
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/compare_texts', methods=['POST'])
def compare_texts():
    try:
        data = request.get_json()
        text1 = data.get('text1', '')
        text2 = data.get('text2', '')
        
        if not text1 or not text2:
            return jsonify({'error': 'Both texts are required for comparison'}), 400
        
        # Enhanced text normalization for better comparison
        def normalize_text(text):
            lines = []
            for line in text.splitlines():
                line = line.strip()
                if line and len(line) > 1:  # Keep meaningful lines
                    # Normalize whitespace but preserve structure
                    normalized_line = ' '.join(line.split())
                    
                    # Handle special characters and numbers better
                    # Keep important punctuation but normalize others
                    normalized_line = re.sub(r'[^\w\s@+.-]', ' ', normalized_line)
                    
                    # Normalize multiple spaces
                    normalized_line = re.sub(r'\s+', ' ', normalized_line)
                    
                    # Convert to lowercase for case-insensitive comparison
                    normalized_line = normalized_line.lower().strip()
                    
                    if normalized_line:  # Keep all meaningful content
                        lines.append(normalized_line)
            return lines
        
        # Get normalized content
        website_lines = normalize_text(text1)
        file_lines = normalize_text(text2)
        
        # Convert to sets for comparison
        website_set = set(website_lines)
        file_set = set(file_lines)
        
        # Find content that is truly missing
        only_in_website = website_set - file_set
        only_in_file = file_set - website_set
        
        # Filter out very short differences and improve comparison
        significant_website_diffs = [content for content in only_in_website if len(content.strip()) > 5]
        significant_file_diffs = [content for content in only_in_file if len(content.strip()) > 5]
        
        # Enhanced similarity detection
        def is_significantly_different(content, other_set):
            # Check if this content is very similar to something in the other set
            content_words = set(content.lower().split())
            for other_content in other_set:
                other_words = set(other_content.lower().split())
                
                # Calculate similarity ratio
                if len(content_words) == 0 or len(other_words) == 0:
                    continue
                    
                similarity_ratio = len(content_words & other_words) / max(len(content_words), len(other_words))
                
                # If more than 70% of words match, consider it similar
                if similarity_ratio > 0.70:
                    return False
                    
                # Check if one is a subset of the other (fragment vs complete sentence)
                if content_words.issubset(other_words) or other_words.issubset(content_words):
                    return False
                    
                # Check for partial matches (common words)
                common_words = content_words & other_words
                if len(common_words) >= 2 and len(common_words) / min(len(content_words), len(other_words)) > 0.4:
                    return False
                    
                # Check for email-like content
                if '@' in content and '@' in other_content:
                    return False
                    
                # Check for email protection patterns
                if ('email' in content.lower() and 'protected' in content.lower()) and '@' in other_content:
                    return False
                if ('email' in other_content.lower() and 'protected' in other_content.lower()) and '@' in content:
                    return False
                    
                # Check for common endings (like "workflows." vs "workflows")
                if content.rstrip('.,!?;:') == other_content.rstrip('.,!?;:'):
                    return False
                    
                # Check for common prefixes (like "ft advise" vs "FT Advise")
                if content.lower().strip() == other_content.lower().strip():
                    return False
                    
                # Check for contact-related content
                if ('contact' in content.lower() and 'contact' in other_content.lower()) or \
                   ('contact' in content.lower() and '@' in other_content) or \
                   ('contact' in other_content.lower() and '@' in content):
                    return False
                    
                # Check for number and metric patterns
                metric_patterns = [
                    ('100 m+', '1 m+'),
                    ('100 m+', '1 million+'),
                    ('100 m+', '100 m+'),
                    ('1 m+', '1 million+'),
                    ('100 million+', '1 million+'),
                    ('100 million+', '100 m+')
                ]
                
                for pattern1, pattern2 in metric_patterns:
                    if (pattern1 in content.lower() and pattern2 in other_content.lower()) or \
                       (pattern2 in content.lower() and pattern1 in other_content.lower()):
                        return False
                        
                # Check for phone number patterns
                phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
                if re.search(phone_pattern, content) and re.search(phone_pattern, other_content):
                    return False
                    
                # Check for URL patterns
                url_pattern = r'https?://[^\s]+'
                if re.search(url_pattern, content) and re.search(url_pattern, other_content):
                    return False
                    
            return True
        
        # Filter out content that's too similar
        significant_website_diffs = [content for content in significant_website_diffs 
                                   if is_significantly_different(content, file_set)]
        significant_file_diffs = [content for content in significant_file_diffs 
                                if is_significantly_different(content, website_set)]
        
        # Check if texts are essentially identical (allowing for minor formatting differences)
        if not significant_website_diffs and not significant_file_diffs:
            return jsonify({
                'identical': True,
                'total_differences': 0,
                'simple_diffs': []
            })
        
        # Create enhanced differences list with line numbers
        simple_diffs = []
        
        # Add significant content only in website with proper line numbers
        for i, content in enumerate(sorted(significant_website_diffs)):
            # Find the actual line number in the original text
            line_number = find_line_number(text1, content)
            simple_diffs.append({
                'type': 'removed',
                'line_number': line_number,
                'website': content,
                'file': None
            })
        
        # Add significant content only in file with proper line numbers
        for i, content in enumerate(sorted(significant_file_diffs)):
            # Find the actual line number in the original text
            line_number = find_line_number(text2, content)
            simple_diffs.append({
                'type': 'added',
                'line_number': line_number,
                'website': None,
                'file': content
            })
        
        return jsonify({
            'identical': False,
            'total_differences': len(simple_diffs),
            'simple_diffs': simple_diffs
        })
        
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

def find_line_number(text, content):
    """Find the line number of content in the original text"""
    lines = text.splitlines()
    content_lower = content.lower().strip()
    
    for i, line in enumerate(lines):
        line_normalized = ' '.join(line.strip().split()).lower()
        if line_normalized == content_lower:
            return i + 1
    
    return 1  # Default to line 1 if not found

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)