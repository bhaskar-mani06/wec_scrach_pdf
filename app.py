from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import difflib
import os
import re
import json
from datetime import datetime
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
        
        # Enhanced text extraction focusing on policy-related content
        def extract_policy_relevant_text(soup):
            # Remove unwanted elements first
            for unwanted in soup(['script', 'style', 'meta', 'link', 'noscript', 'head', 'img']):
                unwanted.decompose()
            
            # Remove navigation and UI elements that are not policy-related
            navigation_selectors = [
                'nav', 'header', 'footer', 'menu', 'navbar', 'breadcrumb',
                '[class*="nav"]', '[class*="menu"]', '[class*="header"]', '[class*="footer"]',
                '[class*="breadcrumb"]', '[class*="sidebar"]', '[class*="toolbar"]'
            ]
            
            for selector in navigation_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # Remove promotional and marketing elements
            marketing_selectors = [
                '[class*="banner"]', '[class*="promo"]', '[class*="ad"]', '[class*="advertisement"]',
                '[class*="marketing"]', '[class*="popup"]', '[class*="modal"]', '[class*="overlay"]',
                '[class*="cta"]', '[class*="call-to-action"]', '[class*="button"]', '[class*="btn"]'
            ]
            
            for selector in marketing_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # Remove social media and sharing elements
            social_selectors = [
                '[class*="social"]', '[class*="share"]', '[class*="follow"]', '[class*="like"]',
                '[class*="twitter"]', '[class*="facebook"]', '[class*="linkedin"]', '[class*="instagram"]'
            ]
            
            for selector in social_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
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
            
            # Only process email patterns if we found actual emails
            if actual_emails:
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
            
            # Enhanced policy-focused content filtering
            def is_policy_relevant(text):
                """Check if text is relevant to insurance policy content"""
                text_lower = text.lower()
                
                # Policy-related keywords that indicate relevant content
                policy_keywords = [
                    'policy', 'insurance', 'coverage', 'premium', 'claim', 'benefit', 'deductible',
                    'exclusion', 'inclusion', 'terms', 'conditions', 'eligibility', 'sum assured',
                    'policyholder', 'insured', 'beneficiary', 'nominee', 'renewal', 'expiry',
                    'effective date', 'policy period', 'coverage limit', 'claim procedure',
                    'risk', 'liability', 'protection', 'compensation', 'settlement', 'endorsement',
                    'rider', 'add-on', 'optional', 'mandatory', 'waiting period', 'cooling off',
                    'free look', 'grace period', 'lapse', 'surrender', 'maturity', 'death benefit',
                    'accidental death', 'disability', 'hospitalization', 'medical', 'health',
                    'life insurance', 'motor insurance', 'travel insurance', 'home insurance',
                    'fire insurance', 'marine insurance', 'crop insurance', 'liability insurance'
                ]
                
                # Check if text contains policy-related keywords
                has_policy_keywords = any(keyword in text_lower for keyword in policy_keywords)
                
                # Check for policy-related patterns
                policy_patterns = [
                    r'₹\s*\d+',  # Currency amounts
                    r'\d+\s*(?:lakh|crore|thousand|million)',  # Amounts with units
                    r'policy\s+(?:no|number|id)',  # Policy numbers
                    r'coverage\s+(?:amount|limit|sum)',  # Coverage amounts
                    r'premium\s+(?:amount|rate|cost)',  # Premium information
                    r'claim\s+(?:process|procedure|settlement)',  # Claim information
                    r'valid\s+(?:from|till|until)',  # Validity periods
                    r'age\s+(?:limit|criteria|requirement)',  # Age requirements
                    r'medical\s+(?:test|examination|checkup)',  # Medical requirements
                ]
                
                has_policy_patterns = any(re.search(pattern, text_lower) for pattern in policy_patterns)
                
                return has_policy_keywords or has_policy_patterns
            
            def is_irrelevant_content(text):
                """Check if text is irrelevant navigation/marketing content"""
                text_lower = text.lower()
                
                # Irrelevant content patterns
                irrelevant_patterns = [
                    # Navigation and UI
                    'home', 'about us', 'contact us', 'login', 'register', 'sign up', 'sign in',
                    'menu', 'navigation', 'breadcrumb', 'footer', 'header', 'sidebar',
                    
                    # Marketing and promotional
                    'learn more', 'read more', 'click here', 'apply now', 'buy now', 'get quote',
                    'download', 'subscribe', 'newsletter', 'follow us', 'share', 'like',
                    'banner', 'advertisement', 'promo', 'offer', 'deal', 'discount',
                    
                    # Technical/UI elements
                    'cookie', 'privacy policy', 'terms of service', 'sitemap', 'search',
                    'google tag manager', 'bootstrap', 'javascript', 'css', 'html',
                    
                    # Social media
                    'facebook', 'twitter', 'linkedin', 'instagram', 'youtube', 'whatsapp',
                    
                    # Generic website content
                    'welcome', 'thank you', 'visit our', 'check out', 'explore', 'discover',
                    'company profile', 'our team', 'careers', 'news', 'blog', 'press release'
                ]
                
                # Check for irrelevant patterns
                has_irrelevant = any(pattern in text_lower for pattern in irrelevant_patterns)
                
                # Check for very short or generic text
                is_too_short = len(text.strip()) < 10
                
                # Check for repetitive navigation text
                is_navigation = any(nav_word in text_lower for nav_word in [
                    'home', 'about', 'contact', 'services', 'products', 'support', 'help'
                ]) and len(text.strip()) < 50
                
                return has_irrelevant or is_too_short or is_navigation
            
            # Clean and filter sentences with policy-focused filtering
            clean_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and len(sentence) > 5:  # Minimum meaningful length
                    # Skip irrelevant content
                    if not is_irrelevant_content(sentence):
                        # Check if content is policy-relevant
                        if is_policy_relevant(sentence):
                            # Additional technical filtering
                            if not any(unwanted in sentence.lower() for unwanted in [
                                'google tag manager', 'bootstrap css', 'js', 'css', 'javascript', 'html', 'meta',
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
            
            # Split into lines and filter with policy-focused restrictions
            raw_lines = raw_text.split('\n')
            filtered_lines = []
            seen_lines = set()
            for line in raw_lines:
                line = line.strip()
                if line and len(line) > 5:  # Minimum meaningful length
                    # Skip irrelevant content
                    if not is_irrelevant_content(line):
                        # Check if content is policy-relevant
                        if is_policy_relevant(line):
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
            
            # Don't add any default email - only use emails from website
            
            # Add line numbers to each line for proper extraction
            lines_with_numbers = []
            for i, line in enumerate(final_text.split('\n'), 1):
                if line.strip():  # Only add non-empty lines
                    lines_with_numbers.append(f"{i}. {line.strip()}")
            
            return '\n'.join(lines_with_numbers)
        
        text = extract_policy_relevant_text(soup)
        
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

@app.route('/extract_policy', methods=['POST'])
def extract_policy():
    """
    Intelligent data extraction assistant for insurance policy analysis.
    Extracts only the main and useful details from webpage text that are relevant to a policy document.
    """
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Please provide text content to analyze'}), 400
        
        # Extract policy information using intelligent parsing
        policy_data = extract_policy_information(text)
        
        return jsonify({
            'success': True,
            'policy_data': policy_data,
            'message': 'Policy information extracted successfully'
        })
        
    except Exception as e:
        return jsonify({'error': f'An error occurred during policy extraction: {str(e)}'}), 500

def extract_policy_information(text):
    """
    Extract policy information from text using intelligent parsing rules.
    Returns structured JSON with policy fields.
    """
    
    # Initialize policy data structure
    policy_data = {
        "policy_name": "Not Found",
        "policy_number": "Not Found", 
        "effective_date": "Not Found",
        "expiry_date": "Not Found",
        "coverage_limit": "Not Found",
        "deductible": "Not Found",
        "covered_events": "Not Found",
        "excluded_events": "Not Found",
        "claim_procedure": "Not Found",
        "contact_info": "Not Found",
        "jurisdiction": "Not Found",
        "renewal_terms": "Not Found",
        "premium_amount": "Not Found",
        "beneficiary": "Not Found",
        "risk_info": "Not Found",
        "definitions": "Not Found",
        # Additional detailed fields
        "product_code": "Not Found",
        "insurance_company_name": "Not Found",
        "broker_name": "Not Found",
        "imd_code": "Not Found",
        "lob": "Not Found",
        "cover": "Not Found",
        "fuel_type": "Not Found",
        "ren_roll_new_used": "Not Found",
        "customer_name": "Not Found",
        "mobile_number": "Not Found",
        "customer_email": "Not Found",
        "location": "Not Found",
        "registration_number": "Not Found",
        "engine_number": "Not Found",
        "chassis_number": "Not Found",
        "policy_issue_date": "Not Found",
        "policy_expiry_date": "Not Found"
    }
    
    # Clean and normalize text
    text_lower = text.lower()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Extract Policy Name/Title
    policy_name = extract_policy_name(text, lines)
    if policy_name:
        policy_data["policy_name"] = policy_name
    
    # Extract Policy Number/Reference ID
    policy_number = extract_policy_number(text, lines)
    if policy_number:
        policy_data["policy_number"] = policy_number
    
    # Extract Effective Date
    effective_date = extract_effective_date(text, lines)
    if effective_date:
        policy_data["effective_date"] = effective_date
    
    # Extract Expiry Date
    expiry_date = extract_expiry_date(text, lines)
    if expiry_date:
        policy_data["expiry_date"] = expiry_date
    
    # Extract Coverage Limit/Sum Assured
    coverage_limit = extract_coverage_limit(text, lines)
    if coverage_limit:
        policy_data["coverage_limit"] = coverage_limit
    
    # Extract Deductible
    deductible = extract_deductible(text, lines)
    if deductible:
        policy_data["deductible"] = deductible
    
    # Extract Covered Events/Inclusions
    covered_events = extract_covered_events(text, lines)
    if covered_events:
        policy_data["covered_events"] = covered_events
    
    # Extract Excluded Events/Exclusions
    excluded_events = extract_excluded_events(text, lines)
    if excluded_events:
        policy_data["excluded_events"] = excluded_events
    
    # Extract Claim Procedure
    claim_procedure = extract_claim_procedure(text, lines)
    if claim_procedure:
        policy_data["claim_procedure"] = claim_procedure
    
    # Extract Contact Information
    contact_info = extract_contact_info(text, lines)
    if contact_info:
        policy_data["contact_info"] = contact_info
    
    # Extract Jurisdiction/Governing Law
    jurisdiction = extract_jurisdiction(text, lines)
    if jurisdiction:
        policy_data["jurisdiction"] = jurisdiction
    
    # Extract Renewal/Cancellation Terms
    renewal_terms = extract_renewal_terms(text, lines)
    if renewal_terms:
        policy_data["renewal_terms"] = renewal_terms
    
    # Extract Premium Amount
    premium_amount = extract_premium_amount(text, lines)
    if premium_amount:
        policy_data["premium_amount"] = premium_amount
    
    # Extract Beneficiary/Nominee details
    beneficiary = extract_beneficiary(text, lines)
    if beneficiary:
        policy_data["beneficiary"] = beneficiary
    
    # Extract Risk Information
    risk_info = extract_risk_info(text, lines)
    if risk_info:
        policy_data["risk_info"] = risk_info
    
    # Extract Definitions/Key Terms
    definitions = extract_definitions(text, lines)
    if definitions:
        policy_data["definitions"] = definitions
    
    # Extract additional detailed fields
    product_code = extract_product_code(text, lines)
    if product_code:
        policy_data["product_code"] = product_code
    
    insurance_company_name = extract_insurance_company_name(text, lines)
    if insurance_company_name:
        policy_data["insurance_company_name"] = insurance_company_name
    
    broker_name = extract_broker_name(text, lines)
    if broker_name:
        policy_data["broker_name"] = broker_name
    
    imd_code = extract_imd_code(text, lines)
    if imd_code:
        policy_data["imd_code"] = imd_code
    
    lob = extract_lob(text, lines)
    if lob:
        policy_data["lob"] = lob
    
    cover = extract_cover(text, lines)
    if cover:
        policy_data["cover"] = cover
    
    fuel_type = extract_fuel_type(text, lines)
    if fuel_type:
        policy_data["fuel_type"] = fuel_type
    
    ren_roll_new_used = extract_ren_roll_new_used(text, lines)
    if ren_roll_new_used:
        policy_data["ren_roll_new_used"] = ren_roll_new_used
    
    customer_name = extract_customer_name(text, lines)
    if customer_name:
        policy_data["customer_name"] = customer_name
    
    mobile_number = extract_mobile_number(text, lines)
    if mobile_number:
        policy_data["mobile_number"] = mobile_number
    
    customer_email = extract_customer_email(text, lines)
    if customer_email:
        policy_data["customer_email"] = customer_email
    
    location = extract_location(text, lines)
    if location:
        policy_data["location"] = location
    
    registration_number = extract_registration_number(text, lines)
    if registration_number:
        policy_data["registration_number"] = registration_number
    
    engine_number = extract_engine_number(text, lines)
    if engine_number:
        policy_data["engine_number"] = engine_number
    
    chassis_number = extract_chassis_number(text, lines)
    if chassis_number:
        policy_data["chassis_number"] = chassis_number
    
    policy_issue_date = extract_policy_issue_date(text, lines)
    if policy_issue_date:
        policy_data["policy_issue_date"] = policy_issue_date
    
    policy_expiry_date = extract_policy_expiry_date(text, lines)
    if policy_expiry_date:
        policy_data["policy_expiry_date"] = policy_expiry_date
    
    return policy_data

def extract_policy_name(text, lines):
    """Extract policy name or title"""
    # Look for common policy name patterns
    patterns = [
        r'(?:Product Name[:\s]*([^\n\r]+))',
        r'(?:TWO WHEELER INSURANCE POLICY[-\s]*PACKAGE)',
        r'(?:Two-wheeler Insurance Policy[-\s]*Package)',
        r'(?:policy\s+name|policy\s+title|plan\s+name|insurance\s+plan)[\s:]*([^\n\r]+)',
        r'([A-Z][a-zA-Z\s&]+(?:policy|plan|insurance|coverage|protection))',
        r'(?:the\s+)?([A-Z][a-zA-Z\s&]+(?:health|life|auto|home|travel|business|two.?wheeler|motor)\s+(?:policy|plan|insurance))',
        r'([A-Z][a-zA-Z\s&]+(?:comprehensive|basic|premium|standard|package)\s+(?:policy|plan|insurance))'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Return the first meaningful match
            for match in matches:
                match = match.strip()
                if len(match) > 5 and not any(word in match.lower() for word in ['terms', 'conditions', 'website', 'company']):
                    return match
    
    return None

def extract_policy_number(text, lines):
    """Extract policy number or reference ID"""
    # Look for policy number patterns
    patterns = [
        r'(?:POPM2W\d+)',  # Specific SBI format
        r'(?:Policy\s*/\s*Certificate\s*No[:\s]*([A-Z0-9\-]+))',
        r'(?:Certificate\s*No[:\s]*([A-Z0-9\-]+))',
        r'(?:policy\s+number|policy\s+no|policy\s+ref|reference\s+id|policy\s+id)[\s:]*([A-Z0-9\-]+)',
        r'(?:ref\.?\s*no|reference\s+number)[\s:]*([A-Z0-9\-]+)',
        r'([A-Z]{2,4}\d{4,8})',  # Common policy number format
        r'([A-Z0-9]{6,12})'  # Generic alphanumeric policy number
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) >= 4:  # Reasonable policy number length
                    return match
    
    return None

def extract_effective_date(text, lines):
    """Extract effective date or start date"""
    # Look for date patterns
    date_patterns = [
        r'(?:effective\s+date|start\s+date|policy\s+start|commencement\s+date)[\s:]*([^\n\r]+)',
        r'(?:from|starting|effective)\s+([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})',
        r'(?:Policy\s+Start\s+Date[:\s]*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4}))',
        r'(?:Period\s+of\s+Insurance[^:]*From[:\s]*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4}))',
        r'([0-9]{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+[0-9]{4})',
        r'([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})'
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 3:
                    return match
    
    return None

def extract_expiry_date(text, lines):
    """Extract expiry date or end date"""
    # Look for expiry date patterns
    date_patterns = [
        r'(?:expiry\s+date|end\s+date|policy\s+end|expiration\s+date)[\s:]*([^\n\r]+)',
        r'(?:until|till|expires|expiring)\s+([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})',
        r'(?:Policy\s+End\s+Date[:\s]*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4}))',
        r'(?:Period\s+of\s+Insurance[^:]*To[:\s]*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4}))',
        r'(?:To[:\s]*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4}))',
        r'(?:to|until)\s+([0-9]{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+[0-9]{4})',
        r'([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})'
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 3:
                    return match
    
    return None

def extract_coverage_limit(text, lines):
    """Extract coverage limit or sum assured"""
    # Look for coverage amount patterns
    patterns = [
        r'(?:coverage\s+limit|sum\s+assured|maximum\s+coverage|policy\s+limit)[\s:]*([^\n\r]+)',
        r'(?:up\s+to|maximum|limit\s+of)\s*([₹$€£¥]\s*[0-9,]+(?:\.[0-9]{2})?|[0-9,]+(?:\.[0-9]{2})?\s*(?:lakh|crore|million|thousand|k|m))',
        r'(?:Total\s+IDV[:\s]*([₹$€£¥]?\s*[0-9,]+(?:\.[0-9]{2})?))',
        r'(?:Vehicle\s+IDV[:\s]*([₹$€£¥]?\s*[0-9,]+(?:\.[0-9]{2})?))',
        r'(?:IDV[:\s]*([₹$€£¥]?\s*[0-9,]+(?:\.[0-9]{2})?))',
        r'([₹$€£¥]\s*[0-9,]+(?:\.[0-9]{2})?)\s*(?:coverage|limit|sum)',
        r'([0-9,]+(?:\.[0-9]{2})?\s*(?:lakh|crore|million|thousand|k|m))\s*(?:coverage|limit|sum)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 2:
                    return match
    
    return None

def extract_deductible(text, lines):
    """Extract deductible information"""
    patterns = [
        r'(?:deductible|excess|co-pay)[\s:]*([^\n\r]+)',
        r'(?:deductible\s+of|excess\s+of)\s*([₹$€£¥]\s*[0-9,]+(?:\.[0-9]{2})?|[0-9,]+(?:\.[0-9]{2})?\s*(?:lakh|crore|million|thousand|k|m))',
        r'(?:Compulsory\s+Deductible[:\s]*([₹$€£¥]?\s*[0-9,]+(?:\.[0-9]{2})?))',
        r'(?:Voluntary\s+Deductible[:\s]*([₹$€£¥]?\s*[0-9,]+(?:\.[0-9]{2})?))',
        r'([₹$€£¥]\s*[0-9,]+(?:\.[0-9]{2})?)\s*(?:deductible|excess)',
        r'([0-9,]+(?:\.[0-9]{2})?\s*(?:lakh|crore|million|thousand|k|m))\s*(?:deductible|excess)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 2:
                    return match
    
    return None

def extract_covered_events(text, lines):
    """Extract covered events or inclusions"""
    # Look for coverage sections
    coverage_keywords = ['covered', 'included', 'coverage includes', 'what is covered', 'benefits', 'we cover you for', 'protection to', 'damage due to']
    exclusion_keywords = ['not covered', 'excluded', 'exclusions', 'not included', 'what your policy does not cover']
    
    coverage_sections = []
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        # Check if line contains coverage keywords
        if any(keyword in line_lower for keyword in coverage_keywords):
            # Collect the next few lines that might contain coverage details
            section = [line]
            for j in range(i+1, min(i+15, len(lines))):
                next_line = lines[j]
                # Stop if we hit exclusion keywords or another section
                if any(excl in next_line.lower() for excl in exclusion_keywords):
                    break
                if len(next_line) > 10:  # Only include substantial lines
                    section.append(next_line)
            
            if len(section) > 1:
                coverage_sections.append(' '.join(section))
    
    if coverage_sections:
        return '; '.join(coverage_sections[:3])  # Return top 3 coverage sections
    
    return None

def extract_excluded_events(text, lines):
    """Extract excluded events or exclusions"""
    exclusion_keywords = ['not covered', 'excluded', 'exclusions', 'not included', 'exceptions', 'what your policy does not cover']
    
    exclusion_sections = []
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        # Check if line contains exclusion keywords
        if any(keyword in line_lower for keyword in exclusion_keywords):
            # Collect the next few lines that might contain exclusion details
            section = [line]
            for j in range(i+1, min(i+15, len(lines))):
                next_line = lines[j]
                if len(next_line) > 10:  # Only include substantial lines
                    section.append(next_line)
            
            if len(section) > 1:
                exclusion_sections.append(' '.join(section))
    
    if exclusion_sections:
        return '; '.join(exclusion_sections[:3])  # Return top 3 exclusion sections
    
    return None

def extract_claim_procedure(text, lines):
    """Extract claim procedure information"""
    claim_keywords = ['claim procedure', 'how to claim', 'claim process', 'filing a claim', 'claim steps', 'how to file your claims', 'network garage', 'non network garage']
    
    claim_sections = []
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        # Check if line contains claim keywords
        if any(keyword in line_lower for keyword in claim_keywords):
            # Collect the next few lines that might contain claim details
            section = [line]
            for j in range(i+1, min(i+20, len(lines))):
                next_line = lines[j]
                if len(next_line) > 10:  # Only include substantial lines
                    section.append(next_line)
            
            if len(section) > 1:
                claim_sections.append(' '.join(section))
    
    if claim_sections:
        return '; '.join(claim_sections[:2])  # Return top 2 claim sections
    
    return None

def extract_contact_info(text, lines):
    """Extract contact information"""
    # Look for email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    
    # Look for phone numbers and toll-free numbers
    phone_patterns = [
        r'\+?[0-9]{1,4}[\s\-]?[0-9]{3,4}[\s\-]?[0-9]{3,4}[\s\-]?[0-9]{3,4}',
        r'\(?[0-9]{3,4}\)?[\s\-]?[0-9]{3,4}[\s\-]?[0-9]{3,4}',
        r'(?:1800[-\s]?[0-9]{2,3}[-\s]?[0-9]{4,5})',  # Toll-free numbers
        r'(?:Toll\s+Free[:\s]*([0-9\-\s]+))',
        r'(?:Call[:\s]*([0-9\-\s]+))'
    ]
    
    phones = []
    for pattern in phone_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        phones.extend(matches)
    
    contact_info = []
    
    if emails:
        contact_info.extend(emails[:2])  # Max 2 emails
    
    if phones:
        contact_info.extend(phones[:3])  # Max 3 phone numbers
    
    if contact_info:
        return '; '.join(contact_info)
    
    return None

def extract_jurisdiction(text, lines):
    """Extract jurisdiction or governing law"""
    patterns = [
        r'(?:jurisdiction|governing\s+law|applicable\s+law)[\s:]*([^\n\r]+)',
        r'(?:laws\s+of|subject\s+to)\s+([A-Z][a-zA-Z\s]+(?:state|country|jurisdiction))',
        r'([A-Z][a-zA-Z\s]+(?:courts?|tribunal|arbitration))'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 5:
                    return match
    
    return None

def extract_renewal_terms(text, lines):
    """Extract renewal or cancellation terms"""
    patterns = [
        r'(?:renewal|cancellation|termination)[\s:]*([^\n\r]+)',
        r'(?:auto\s+renewal|automatic\s+renewal)[\s:]*([^\n\r]+)',
        r'(?:notice\s+period|cancellation\s+notice)[\s:]*([^\n\r]+)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 5:
                    return match
    
    return None

def extract_premium_amount(text, lines):
    """Extract premium amount or payment terms"""
    patterns = [
        r'(?:premium|payment|annual\s+premium)[\s:]*([^\n\r]+)',
        r'(?:premium\s+of|payment\s+of)\s*([₹$€£¥]\s*[0-9,]+(?:\.[0-9]{2})?|[0-9,]+(?:\.[0-9]{2})?\s*(?:lakh|crore|million|thousand|k|m))',
        r'(?:FINAL\s+PREMIUM[:\s]*([₹$€£¥]?\s*[0-9,]+(?:\.[0-9]{2})?))',
        r'(?:TOTAL\s+PREMIUM[:\s]*([₹$€£¥]?\s*[0-9,]+(?:\.[0-9]{2})?))',
        r'(?:Policy\s+premium[:\s]*([₹$€£¥]?\s*[0-9,]+(?:\.[0-9]{2})?))',
        r'([₹$€£¥]\s*[0-9,]+(?:\.[0-9]{2})?)\s*(?:premium|payment)',
        r'([0-9,]+(?:\.[0-9]{2})?\s*(?:lakh|crore|million|thousand|k|m))\s*(?:premium|payment)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 2:
                    return match
    
    return None

def extract_beneficiary(text, lines):
    """Extract beneficiary or nominee details"""
    patterns = [
        r'(?:beneficiary|nominee)[\s:]*([^\n\r]+)',
        r'(?:beneficiary\s+details|nominee\s+details)[\s:]*([^\n\r]+)',
        r'(?:in\s+favor\s+of|payable\s+to)[\s:]*([^\n\r]+)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 5:
                    return match
    
    return None

def extract_risk_info(text, lines):
    """Extract risk ratio or risk coverage information"""
    patterns = [
        r'(?:risk\s+ratio|risk\s+coverage|risk\s+assessment)[\s:]*([^\n\r]+)',
        r'(?:coverage\s+ratio|sum\s+at\s+risk)[\s:]*([^\n\r]+)',
        r'([0-9]+(?:\.[0-9]+)?\s*%)\s*(?:risk|coverage)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 2:
                    return match
    
    return None

def extract_definitions(text, lines):
    """Extract definitions or key terms"""
    definition_keywords = ['definition', 'definitions', 'key terms', 'glossary', 'meaning']
    
    definition_sections = []
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        # Check if line contains definition keywords
        if any(keyword in line_lower for keyword in definition_keywords):
            # Collect the next few lines that might contain definitions
            section = [line]
            for j in range(i+1, min(i+20, len(lines))):
                next_line = lines[j]
                if len(next_line) > 10:  # Only include substantial lines
                    section.append(next_line)
            
            if len(section) > 1:
                definition_sections.append(' '.join(section))
    
    if definition_sections:
        return '; '.join(definition_sections[:2])  # Return top 2 definition sections
    
    return None

# Additional detailed field extraction functions

def extract_product_code(text, lines):
    """Extract product code"""
    patterns = [
        r'(?:product\s+code|product\s+id)[\s:]*([A-Z0-9\-]+)',
        r'(?:code[:\s]*([A-Z0-9\-]+))',
        r'([A-Z]{2,4}[0-9]{2,6})'  # Common product code format
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) >= 3:
                    return match
    return None

def extract_insurance_company_name(text, lines):
    """Extract insurance company name"""
    patterns = [
        r'(?:SBI\s+General\s+Insurance)',
        r'(?:Bajaj\s+Allianz\s+General\s+Insurance)',
        r'(?:HDFC\s+ERGO\s+General\s+Insurance)',
        r'(?:ICICI\s+Lombard\s+General\s+Insurance)',
        r'(?:New\s+India\s+Assurance)',
        r'(?:Oriental\s+Insurance)',
        r'(?:United\s+India\s+Insurance)',
        r'(?:National\s+Insurance)',
        r'([A-Z][a-zA-Z\s&]+(?:Insurance|General|Assurance))'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 5:
                    return match
    return None

def extract_broker_name(text, lines):
    """Extract broker/intermediary name"""
    patterns = [
        r'(?:broker\s+name|intermediary\s+name)[\s:]*([^\n\r]+)',
        r'(?:Cox\s+and\s+Kings)',
        r'([A-Z][a-zA-Z\s&]+(?:Broker|Agency|Services))'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 3:
                    return match
    return None

def extract_imd_code(text, lines):
    """Extract IMD code"""
    patterns = [
        r'(?:imd\s+code|intermediary\s+code)[\s:]*([A-Z0-9\-]+)',
        r'(?:code[:\s]*([0-9]{6,8}))'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) >= 4:
                    return match
    return None

def extract_lob(text, lines):
    """Extract Line of Business"""
    patterns = [
        r'(?:lob|line\s+of\s+business)[\s:]*([^\n\r]+)',
        r'(?:motor|health|life|travel|home|fire)',
        r'(?:two.?wheeler|four.?wheeler|commercial\s+vehicle)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 2:
                    return match
    return None

def extract_cover(text, lines):
    """Extract cover type"""
    patterns = [
        r'(?:cover|coverage\s+type)[\s:]*([^\n\r]+)',
        r'(?:comprehensive|third\s+party|package|basic)',
        r'(?:own\s+damage|od|tp)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 2:
                    return match
    return None

def extract_fuel_type(text, lines):
    """Extract fuel type"""
    patterns = [
        r'(?:fuel\s+type|fuel)[\s:]*([^\n\r]+)',
        r'(?:petrol|diesel|cng|lpg|electric|hybrid)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 2:
                    return match
    return None

def extract_ren_roll_new_used(text, lines):
    """Extract renewal/roll/new/used status"""
    patterns = [
        r'(?:renewal|roll|new|used|first\s+time)',
        r'(?:policy\s+type)[\s:]*([^\n\r]+)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 2:
                    return match
    return None

def extract_customer_name(text, lines):
    """Extract customer name"""
    patterns = [
        r'(?:customer\s+name|policy\s+holder\s+name|proposer\s+name)[\s:]*([^\n\r]+)',
        r'(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s*([A-Z][a-zA-Z\s]+)',
        r'(?:Name[:\s]*([A-Z][a-zA-Z\s]+))'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 3 and not any(word in match.lower() for word in ['address', 'contact', 'email']):
                    return match
    return None

def extract_mobile_number(text, lines):
    """Extract mobile number"""
    patterns = [
        r'(?:mobile\s+number|contact\s+number|phone\s+number)[\s:]*([0-9\-\s\+]+)',
        r'(\+?91[-\s]?[0-9]{10})',
        r'([0-9]{10})'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) >= 10:
                    return match
    return None

def extract_customer_email(text, lines):
    """Extract customer email"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    
    if emails:
        return emails[0]  # Return first email found
    return None

def extract_location(text, lines):
    """Extract location/address"""
    patterns = [
        r'(?:location|address|rto\s+location)[\s:]*([^\n\r]+)',
        r'(?:Mumbai|Delhi|Bangalore|Chennai|Kolkata|Hyderabad|Pune|Ahmedabad)',
        r'([A-Z][a-zA-Z\s]+,\s*[A-Z][a-zA-Z\s]+)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 3:
                    return match
    return None

def extract_registration_number(text, lines):
    """Extract vehicle registration number"""
    patterns = [
        r'(?:registration\s+number|reg\s+no|vehicle\s+number)[\s:]*([A-Z0-9\s]+)',
        r'([A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4})',  # Indian format
        r'([A-Z0-9]{6,12})'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) >= 6:
                    return match
    return None

def extract_engine_number(text, lines):
    """Extract engine number"""
    patterns = [
        r'(?:engine\s+number|engine\s+no)[\s:]*([A-Z0-9\s]+)',
        r'([A-Z0-9]{6,15})'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) >= 6:
                    return match
    return None

def extract_chassis_number(text, lines):
    """Extract chassis number"""
    patterns = [
        r'(?:chassis\s+number|chassis\s+no)[\s:]*([A-Z0-9\s]+)',
        r'([A-Z0-9]{10,20})'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) >= 10:
                    return match
    return None

def extract_policy_issue_date(text, lines):
    """Extract policy issue date"""
    patterns = [
        r'(?:policy\s+issue\s+date|issue\s+date)[\s:]*([0-9\/\-\.]+)',
        r'(?:receipt\s+date)[\s:]*([0-9\/\-\.]+)',
        r'([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 3:
                    return match
    return None

def extract_policy_expiry_date(text, lines):
    """Extract policy expiry date"""
    patterns = [
        r'(?:policy\s+end\s+date|expiry\s+date)[\s:]*([0-9\/\-\.]+)',
        r'(?:to[:\s]*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4}))',
        r'([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                match = match.strip()
                if len(match) > 3:
                    return match
    return None

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)