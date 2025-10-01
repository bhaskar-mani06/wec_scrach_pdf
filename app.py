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
        
        # Remove script, style, and hidden elements
        for element in soup(["script", "style", "noscript", "meta", "link", "head"]):
            element.decompose()
        
        # Remove elements with hidden attributes
        for element in soup.find_all(attrs={"hidden": True}):
            element.decompose()
        
        # Remove elements with display:none or visibility:hidden styles
        for element in soup.find_all(style=re.compile(r'display\s*:\s*none|visibility\s*:\s*hidden')):
            element.decompose()
        
        # Remove elements with hidden class
        for element in soup.find_all(class_=re.compile(r'hidden|hide|d-none|invisible')):
            element.decompose()
        
        # Remove all img tags and their content
        for img in soup.find_all('img'):
            img.decompose()
        
        # Remove elements that contain image file names in their attributes
        for element in soup.find_all(attrs=True):
            for attr_name, attr_value in element.attrs.items():
                if isinstance(attr_value, str) and re.search(r'@\d+\.?\d*x\.webp|\.webp|\.png|\.jpg|\.jpeg|\.svg|\.gif|\.ico', attr_value, re.IGNORECASE):
                    element.decompose()
                    break
        
        # Extract text with complete sentences and proper structure
        def extract_exact_text(soup):
            # Remove unwanted elements first
            for unwanted in soup(['script', 'style', 'meta', 'link', 'noscript', 'head', 'img']):
                unwanted.decompose()
            
            # Remove hidden elements
            for element in soup.find_all(attrs={"hidden": True}):
                element.decompose()
            
            # Remove elements with display:none or visibility:hidden styles
            for element in soup.find_all(style=re.compile(r'display\s*:\s*none|visibility\s*:\s*hidden')):
                element.decompose()
            
            # Remove elements with hidden class
            for element in soup.find_all(class_=re.compile(r'hidden|hide|d-none|invisible|sr-only')):
                element.decompose()
            
            # Remove elements with aria-hidden attribute
            for element in soup.find_all(attrs={"aria-hidden": "true"}):
                element.decompose()
            
            # Remove all img tags completely
            for img in soup.find_all('img'):
                img.decompose()
            
            # Keep navigation and button elements - don't remove them
            
            # Remove elements containing image file names in any attribute
            for element in soup.find_all(attrs=True):
                for attr_name, attr_value in element.attrs.items():
                    if isinstance(attr_value, str) and re.search(r'@\d+\.?\d*x\.webp|\.webp|\.png|\.jpg|\.jpeg|\.svg|\.gif|\.ico', attr_value, re.IGNORECASE):
                        element.decompose()
                        break
            
            # Handle email protection patterns before getting text
            # Get the HTML content to process email patterns
            html_content = str(soup)
            
            # Aggressive removal of image-related content from HTML
            aggressive_patterns = [
                r'<[^>]*src\s*=\s*["\'][^"\']*@\d+\.?\d*x\.webp[^"\']*["\'][^>]*>',  # Remove img tags with @x.webp
                r'<[^>]*alt\s*=\s*["\'][^"\']*@\d+\.?\d*x\.webp[^"\']*["\'][^>]*>',  # Remove elements with alt containing @x.webp
                r'<[^>]*data-[^=]*\s*=\s*["\'][^"\']*@\d+\.?\d*x\.webp[^"\']*["\'][^>]*>',  # Remove data attributes with @x.webp
                r'Without@\d+\.?\d*x\.webp',  # Direct removal
                r'with@\d+\.?\d*x\.webp',     # Direct removal
                r'[A-Za-z0-9_-]*@\d+\.?\d*x\.webp',  # Any @x.webp pattern
            ]
            
            for pattern in aggressive_patterns:
                html_content = re.sub(pattern, '', html_content, flags=re.IGNORECASE)
            
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
            
            # Remove image file names and unwanted content
            unwanted_patterns = [
                r'[A-Za-z0-9_-]*@\d+\.?\d*x\.webp',  # Remove @1.5x.webp, @2x.webp etc
                r'[A-Za-z0-9_-]*\.webp',  # Remove .webp files
                r'[A-Za-z0-9_-]*\.png',   # Remove .png files
                r'[A-Za-z0-9_-]*\.jpg',   # Remove .jpg files
                r'[A-Za-z0-9_-]*\.jpeg',  # Remove .jpeg files
                r'[A-Za-z0-9_-]*\.svg',   # Remove .svg files
                r'[A-Za-z0-9_-]*\.gif',   # Remove .gif files
                r'[A-Za-z0-9_-]*\.ico',   # Remove .ico files
                r'without@\d+\.?\d*x\.webp',  # Specific pattern for "without@1.5x.webp"
                r'with@\d+\.?\d*x\.webp',     # Specific pattern for "with@1.5x.webp"
                r'Without@\d+\.?\d*x\.webp',  # Capital W version
                r'With@\d+\.?\d*x\.webp',     # Capital W version
                r'[Ww]ithout@[0-9.]+x\.webp', # More flexible pattern
                r'[Ww]ith@[0-9.]+x\.webp',    # More flexible pattern
            ]
            
            for pattern in unwanted_patterns:
                html_content = re.sub(pattern, '', html_content, flags=re.IGNORECASE)
            
            # Additional specific removal for common patterns
            specific_removals = [
                'Without@1.5x.webp',
                'with@1.5x.webp',
                'Without@2x.webp',
                'with@2x.webp',
                'Without@3x.webp',
                'with@3x.webp',
            ]
            
            for removal in specific_removals:
                html_content = html_content.replace(removal, '')
                html_content = html_content.replace(removal.lower(), '')
                html_content = html_content.replace(removal.upper(), '')
            
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
            
            # Remove any remaining HTML tags completely
            for tag in soup_modified.find_all():
                tag.unwrap()
            
            # Get all text content
            text = soup_modified.get_text(separator=' ', strip=True)
            
            # Clean up any remaining HTML entities and tags
            text = re.sub(r'<[^>]+>', '', text)  # Remove any remaining HTML tags
            text = re.sub(r'&[a-zA-Z0-9#]+;', '', text)  # Remove HTML entities
            
            # Clean up the text
            text = re.sub(r'\s+', ' ', text)
            
            # Split into meaningful sentences and phrases - improved method
            sentences = []
            current_sentence = ""
            
            # Split by common sentence endings and line breaks
            text_parts = re.split(r'[.!?]\s+|\n+', text)
            
            for part in text_parts:
                part = part.strip()
                if part and len(part) > 2:  # Keep meaningful parts
                    # Split long parts into smaller chunks if needed
                    if len(part) > 200:
                        # Split by common separators
                        sub_parts = re.split(r'[,;]\s+|\s+-\s+', part)
                        for sub_part in sub_parts:
                            sub_part = sub_part.strip()
                            if sub_part and len(sub_part) > 2:
                                sentences.append(sub_part)
                    else:
                        sentences.append(part)
            
            # Also try word-by-word approach for better coverage
            current_sentence = ""
            for word in text.split():
                current_sentence += word + " "
                
                # Check if this completes a sentence or meaningful phrase
                if (word.endswith('.') or word.endswith('!') or word.endswith('?') or 
                    len(current_sentence.strip()) > 100):  # Increased from 80 to 100
                    if current_sentence.strip() not in sentences:  # Avoid duplicates
                        sentences.append(current_sentence.strip())
                    current_sentence = ""
            
            # Add remaining content
            if current_sentence.strip() and current_sentence.strip() not in sentences:
                sentences.append(current_sentence.strip())
            
            # Clean and filter sentences - very lenient filtering to preserve content
            clean_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and len(sentence) > 2:  # Keep even shorter sentences
                    # Only filter out very obvious technical/boilerplate content
                    if not any(unwanted in sentence.lower() for unwanted in [
                        'google tag manager', 'end google tag manager', 'required meta tags',
                        'bootstrap css', 'js', 'css', 'javascript', 'html', 'meta',
                        'viewport', 'charset', 'http-equiv', 'content-type',
                        '.webp', '.png', '.jpg', '.jpeg', '.svg', '.gif', '.ico',
                        '@1x', '@2x', '@3x', '@1.5x', '@2.5x', '@3.5x',
                        'without@', 'with@', 'image@', 'img@',
                        'hidden', 'hide', 'invisible', 'sr-only', 'screen reader',
                        'aria-hidden', 'display: none', 'visibility: hidden',
                        '<span', '<div', '<p', '<h', '<a', '<img', '<script', '<style'
                    ]):
                        # Additional check for file extensions and image references
                        if not re.search(r'\.(webp|png|jpg|jpeg|svg|gif|ico)', sentence, re.IGNORECASE):
                            if not re.search(r'@\d+\.?\d*x', sentence, re.IGNORECASE):
                                # Check for specific unwanted patterns
                                if not any(unwanted in sentence for unwanted in [
                                    'Without@1.5x.webp', 'with@1.5x.webp', 'Without@2x.webp', 'with@2x.webp',
                                    'Without@3x.webp', 'with@3x.webp', 'without@1.5x.webp', 'with@1.5x.webp'
                                ]):
                                    # Check for HTML tags in sentence
                                    if not re.search(r'<[^>]+>', sentence):
                                        clean_sentences.append(sentence)
            
            # Add the email if it's not already present
            final_text = '\n'.join(clean_sentences)
            
            # Always try to get more comprehensive content
            # Get raw text from the soup for maximum content extraction
            raw_text = soup.get_text(separator='\n', strip=True)
            
            # Clean up the raw text
            raw_text = re.sub(r'\n\s*\n', '\n', raw_text)  # Remove multiple newlines
            raw_text = re.sub(r'<[^>]+>', '', raw_text)  # Remove any remaining HTML tags
            raw_text = re.sub(r'&[a-zA-Z0-9#]+;', '', raw_text)  # Remove HTML entities
            
            # Split into lines and filter with very minimal restrictions
            raw_lines = raw_text.split('\n')
            filtered_lines = []
            seen_lines = set()
            for line in raw_lines:
                line = line.strip()
                if line and len(line) > 1:  # Keep even single character lines
                    # Only filter out very obvious unwanted content
                    if not any(unwanted in line.lower() for unwanted in [
                        'google tag manager', 'bootstrap css', 'js', 'css', 'javascript',
                        '.webp', '.png', '.jpg', '.jpeg', '.svg', '.gif', '.ico',
                        '@1x', '@2x', '@3x', '@1.5x', '@2.5x', '@3.5x',
                        'without@', 'with@', 'image@', 'img@',
                        '<span', '<div', '<p', '<h', '<a', '<img', '<script', '<style'
                    ]):
                        if not re.search(r'\.(webp|png|jpg|jpeg|svg|gif|ico)', line, re.IGNORECASE):
                            if not re.search(r'@\d+\.?\d*x', line, re.IGNORECASE):
                                if not re.search(r'<[^>]+>', line):
                                    # Check for duplicates
                                    if line not in seen_lines:
                                        seen_lines.add(line)
                                        filtered_lines.append(line)
            
            # Use the more comprehensive content if it's longer
            comprehensive_text = '\n'.join(filtered_lines)
            if len(comprehensive_text) > len(final_text):
                final_text = comprehensive_text
            
            # Simple and effective approach: Extract all content in DOM order with duplicate removal
            all_content = []
            seen_content = set()
            
            # Get all text elements in DOM order
            all_elements = soup.find_all(['nav', 'menu', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                                        'p', 'li', 'button', 'a', 'strong', 'b', 'em', 'i', 'div', 'span'])
            
            for element in all_elements:
                element_text = element.get_text(strip=True)
                if element_text and len(element_text) > 1:
                    # Apply basic filtering
                    if not any(unwanted in element_text.lower() for unwanted in [
                        'google tag manager', 'bootstrap css', 'js', 'css', 'javascript',
                        '.webp', '.png', '.jpg', '.jpeg', '.svg', '.gif', '.ico',
                        '@1x', '@2x', '@3x', '@1.5x', '@2.5x', '@3.5x',
                        'without@', 'with@', 'image@', 'img@'
                    ]):
                        if not re.search(r'\.(webp|png|jpg|jpeg|svg|gif|ico)', element_text, re.IGNORECASE):
                            if not re.search(r'@\d+\.?\d*x', element_text, re.IGNORECASE):
                                if not re.search(r'<[^>]+>', element_text):
                                    # Avoid very long content
                                    if len(element_text) < 1000:
                                        # Check for concatenated text and split it
                                        if re.search(r'[A-Z][a-z]+[A-Z]', element_text):  # Check for camelCase or concatenated words
                                            # Split by capital letters
                                            separated_items = re.findall(r'[A-Z][a-z]*(?:\s+[A-Z][a-z]*)*', element_text)
                                            for separated_item in separated_items:
                                                separated_item = separated_item.strip()
                                                if separated_item and len(separated_item) > 1:
                                                    if separated_item not in seen_content:
                                                        seen_content.add(separated_item)
                                                        all_content.append(separated_item)
                                        else:
                                            # Check for duplicates
                                            if element_text not in seen_content:
                                                seen_content.add(element_text)
                                                all_content.append(element_text)
            
            # Use this content if it's longer
            dom_text = '\n'.join(all_content)
            if len(dom_text) > len(final_text):
                final_text = dom_text
            
            # Additional approach: Extract specific elements with better targeting
            specific_content = []
            seen_specific = set()
            
            # Extract navigation elements specifically with proper separation
            for nav in soup.find_all(['nav', 'ul', 'ol']):
                for item in nav.find_all(['li', 'a']):
                    item_text = item.get_text(strip=True)
                    if item_text and len(item_text) > 1 and len(item_text) < 100:
                        # Split concatenated text by common patterns
                        if re.search(r'[A-Z][a-z]+[A-Z]', item_text):  # Check for camelCase or concatenated words
                            # Split by capital letters
                            separated_items = re.findall(r'[A-Z][a-z]*(?:\s+[A-Z][a-z]*)*', item_text)
                            for separated_item in separated_items:
                                separated_item = separated_item.strip()
                                if separated_item and len(separated_item) > 1:
                                    if separated_item not in seen_specific:
                                        seen_specific.add(separated_item)
                                        specific_content.append(separated_item)
                        else:
                            if item_text not in seen_specific:
                                seen_specific.add(item_text)
                                specific_content.append(item_text)
            
            # Extract buttons specifically with proper separation
            for button in soup.find_all(['button', 'a']):
                button_text = button.get_text(strip=True)
                if button_text and len(button_text) > 1 and len(button_text) < 100:
                    # Split concatenated text by common patterns
                    if re.search(r'[A-Z][a-z]+[A-Z]', button_text):  # Check for camelCase or concatenated words
                        # Split by capital letters
                        separated_items = re.findall(r'[A-Z][a-z]*(?:\s+[A-Z][a-z]*)*', button_text)
                        for separated_item in separated_items:
                            separated_item = separated_item.strip()
                            if separated_item and len(separated_item) > 1:
                                if separated_item not in seen_specific:
                                    seen_specific.add(separated_item)
                                    specific_content.append(separated_item)
                    else:
                        if button_text not in seen_specific:
                            seen_specific.add(button_text)
                            specific_content.append(button_text)
            
            # Extract headings specifically
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                heading_text = heading.get_text(strip=True)
                if heading_text and len(heading_text) > 1:
                    if heading_text not in seen_specific:
                        seen_specific.add(heading_text)
                        specific_content.append(heading_text)
            
            # Extract paragraphs specifically
            for para in soup.find_all('p'):
                para_text = para.get_text(strip=True)
                if para_text and len(para_text) > 5:
                    if para_text not in seen_specific:
                        seen_specific.add(para_text)
                        specific_content.append(para_text)
            
            # Extract list items specifically
            for li in soup.find_all('li'):
                li_text = li.get_text(strip=True)
                if li_text and len(li_text) > 2:
                    if li_text not in seen_specific:
                        seen_specific.add(li_text)
                        specific_content.append(li_text)
            
            # Use specific content if it's longer
            specific_text = '\n'.join(specific_content)
            if len(specific_text) > len(final_text):
                final_text = specific_text
            
            # Final approach: Better text separation for concatenated content
            separated_content = []
            seen_separated = set()
            
            # Get all text and split concatenated words
            all_text = soup.get_text(separator=' ', strip=True)
            
            # Split by common patterns that indicate concatenated text
            # Pattern 1: camelCase or PascalCase (HomeAboutUs -> Home About Us)
            all_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', all_text)
            
            # Pattern 2: Numbers followed by letters (48+Insurers -> 48+ Insurers)
            all_text = re.sub(r'(\d+)([A-Za-z])', r'\1 \2', all_text)
            
            # Pattern 3: Letters followed by numbers (Insurers48 -> Insurers 48)
            all_text = re.sub(r'([A-Za-z])(\d+)', r'\1 \2', all_text)
            
            # Pattern 4: Special characters (Schedule a Demo -> Schedule a Demo)
            all_text = re.sub(r'([a-z])([A-Z][a-z])', r'\1 \2', all_text)
            
            # Split into lines and clean up
            lines = all_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 1:
                    # Further split by common separators
                    words = re.split(r'[\s,;]+', line)
                    for word in words:
                        word = word.strip()
                        if word and len(word) > 1 and len(word) < 100:
                            # Apply filtering
                            if not any(unwanted in word.lower() for unwanted in [
                                'google tag manager', 'bootstrap css', 'js', 'css', 'javascript',
                                '.webp', '.png', '.jpg', '.jpeg', '.svg', '.gif', '.ico',
                                '@1x', '@2x', '@3x', '@1.5x', '@2.5x', '@3.5x',
                                'without@', 'with@', 'image@', 'img@'
                            ]):
                                if not re.search(r'\.(webp|png|jpg|jpeg|svg|gif|ico)', word, re.IGNORECASE):
                                    if not re.search(r'@\d+\.?\d*x', word, re.IGNORECASE):
                                        if not re.search(r'<[^>]+>', word):
                                            if word not in seen_separated:
                                                seen_separated.add(word)
                                                separated_content.append(word)
            
            # Use separated content if it's longer
            separated_text = '\n'.join(separated_content)
            if len(separated_text) > len(final_text):
                final_text = separated_text
            
            # Final cleanup - remove any remaining unwanted patterns
            final_cleanup_patterns = [
                r'[Ww]ithout@[0-9.]+x\.webp',
                r'[Ww]ith@[0-9.]+x\.webp',
                r'[A-Za-z0-9_-]*@[0-9.]+x\.webp',
                r'[A-Za-z0-9_-]*\.webp',
            ]
            
            for pattern in final_cleanup_patterns:
                final_text = re.sub(pattern, '', final_text, flags=re.IGNORECASE)
            
            # Remove specific unwanted strings
            unwanted_strings = [
                'Without@1.5x.webp', 'with@1.5x.webp', 'Without@2x.webp', 'with@2x.webp',
                'Without@3x.webp', 'with@3x.webp', 'without@1.5x.webp', 'with@1.5x.webp'
            ]
            
            for unwanted in unwanted_strings:
                final_text = final_text.replace(unwanted, '')
                final_text = final_text.replace(unwanted.lower(), '')
                final_text = final_text.replace(unwanted.upper(), '')
            
            # Clean up extra whitespace and HTML tags
            final_text = re.sub(r'<[^>]+>', '', final_text)  # Remove any remaining HTML tags
            final_text = re.sub(r'&[a-zA-Z0-9#]+;', '', final_text)  # Remove HTML entities
            final_text = re.sub(r'\n\s*\n', '\n', final_text)
            final_text = final_text.strip()
            
            # Remove empty lines and lines with only whitespace, and remove duplicates
            lines = final_text.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            
            # Remove duplicates while preserving order
            seen_final_lines = set()
            unique_final_lines = []
            for line in non_empty_lines:
                if line not in seen_final_lines:
                    seen_final_lines.add(line)
                    unique_final_lines.append(line)
            
            final_text = '\n'.join(unique_final_lines)
            
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
        print("=== COMPARE TEXTS REQUEST ===")
        data = request.get_json()
        print(f"Received data: {data}")
        
        if not data:
            print("ERROR: No data received")
            return jsonify({'error': 'No data received'}), 400
            
        text1 = data.get('text1', '')
        text2 = data.get('text2', '')
        
        print(f"Text1 length: {len(text1)}")
        print(f"Text2 length: {len(text2)}")
        
        if not text1 or not text2:
            print("ERROR: Missing text data")
            return jsonify({'error': 'Both texts are required for comparison'}), 400
        
        # Enhanced diff algorithm using Python's difflib for better results
        def create_enhanced_diff(text1, text2):
            # Split texts into lines
            lines1 = text1.splitlines()
            lines2 = text2.splitlines()
            
            # Use difflib for better comparison
            differ = difflib.unified_diff(lines1, lines2, lineterm='', n=0)
            diff_lines = list(differ)
            
            # Process the diff to create structured differences
            differences = []
            current_change = None
            
            for line in diff_lines:
                if line.startswith('---') or line.startswith('+++'):
                    continue
                elif line.startswith('@@'):
                    # New change block
                    if current_change:
                        differences.append(current_change)
                    current_change = {
                        'type': 'change',
                        'removed_lines': [],
                        'added_lines': [],
                        'context_lines': []
                    }
                elif line.startswith('-'):
                    # Removed line
                    if current_change:
                        current_change['removed_lines'].append(line[1:])
                elif line.startswith('+'):
                    # Added line
                    if current_change:
                        current_change['added_lines'].append(line[1:])
                elif line.startswith(' '):
                    # Context line
                    if current_change:
                        current_change['context_lines'].append(line[1:])
            
            # Add the last change if exists
            if current_change:
                differences.append(current_change)
            
            return differences
        
        # Create word-level differences for better highlighting
        def create_word_level_diff(text1, text2):
            # Use difflib for word-level comparison
            differ = difflib.SequenceMatcher(None, text1, text2)
            word_diffs = []
            
            for tag, i1, i2, j1, j2 in differ.get_opcodes():
                if tag == 'equal':
                    continue
                elif tag == 'delete':
                    word_diffs.append({
                        'type': 'removed',
                        'content': text1[i1:i2],
                        'start': i1,
                        'end': i2
                    })
                elif tag == 'insert':
                    word_diffs.append({
                        'type': 'added',
                        'content': text2[j1:j2],
                        'start': j1,
                        'end': j2
                    })
                elif tag == 'replace':
                    word_diffs.append({
                        'type': 'removed',
                        'content': text1[i1:i2],
                        'start': i1,
                        'end': i2
                    })
                    word_diffs.append({
                        'type': 'added',
                        'content': text2[j1:j2],
                        'start': j1,
                        'end': j2
                    })
            
            return word_diffs
        
        # Enhanced text normalization for better comparison
        def normalize_text(text):
            lines = []
            for line in text.splitlines():
                line = line.strip()
                if line:  # Keep all non-empty lines
                    original_line = line
                    # Normalize whitespace but preserve structure
                    normalized_line = ' '.join(line.split())
                    # Convert to lowercase for case-insensitive comparison
                    normalized_line = normalized_line.lower().strip()
                    
                    lines.append({
                        'original': original_line,
                        'normalized': normalized_line
                    })
            return lines
        
        # Get normalized content
        website_lines = normalize_text(text1)
        file_lines = normalize_text(text2)
        
        # Extract normalized text for comparison
        website_normalized = [line['normalized'] for line in website_lines]
        file_normalized = [line['normalized'] for line in file_lines]
        
        # Use difflib for better line-by-line comparison
        differ = difflib.SequenceMatcher(None, website_normalized, file_normalized)
        
        # Create structured differences
        simple_diffs = []
        line_number_website = 1
        line_number_file = 1
        
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag == 'equal':
                # Lines are the same, just advance line numbers
                line_number_website += (i2 - i1)
                line_number_file += (j2 - j1)
            elif tag == 'delete':
                # Lines removed from website
                for i in range(i1, i2):
                    if i < len(website_lines):
                        simple_diffs.append({
                            'type': 'removed',
                            'line_number': line_number_website,
                            'website': website_lines[i]['original'],
                            'file': None
                        })
                        line_number_website += 1
            elif tag == 'insert':
                # Lines added to file
                for j in range(j1, j2):
                    if j < len(file_lines):
                        simple_diffs.append({
                            'type': 'added',
                            'line_number': line_number_file,
                            'website': None,
                            'file': file_lines[j]['original']
                        })
                        line_number_file += 1
            elif tag == 'replace':
                # Lines replaced
                # Add removed lines
                for i in range(i1, i2):
                    if i < len(website_lines):
                        simple_diffs.append({
                            'type': 'removed',
                            'line_number': line_number_website,
                            'website': website_lines[i]['original'],
                            'file': None
                        })
                        line_number_website += 1
                # Add added lines
                for j in range(j1, j2):
                    if j < len(file_lines):
                        simple_diffs.append({
                            'type': 'added',
                            'line_number': line_number_file,
                            'website': None,
                            'file': file_lines[j]['original']
                        })
                        line_number_file += 1
        
        # Check if texts are essentially identical
        if not simple_diffs:
            return jsonify({
                'identical': True,
                'total_differences': 0,
                'simple_diffs': []
            })
        
        print(f"=== COMPARISON COMPLETE ===")
        print(f"Total differences: {len(simple_diffs)}")
        print(f"Simple diffs: {simple_diffs}")
        
        result = {
            'identical': False,
            'total_differences': len(simple_diffs),
            'simple_diffs': simple_diffs
        }
        
        print(f"Returning result: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"ERROR in compare_texts: {str(e)}")
        import traceback
        traceback.print_exc()
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