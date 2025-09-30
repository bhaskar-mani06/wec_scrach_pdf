# Web Scraping Tool with Text Comparison

A powerful web scraping tool that extracts text from websites and compares it with uploaded text files to find differences.

## Features

- **Website Text Extraction**: Extract clean text from any website URL
- **File Upload**: Upload .txt files for comparison
- **Smart Text Comparison**: Intelligent comparison with normalization
- **Email Protection Handling**: Automatically handles email protection patterns
- **Metric Pattern Recognition**: Handles different number formats (1M+, 100M+, etc.)
- **Contact Text Association**: Links contact information with email addresses

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/web-scraping-tool.git
cd web-scraping-tool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and go to `http://localhost:5000`

## Usage

1. **Extract Website Text**: Enter a website URL and click "Extract Text"
2. **Upload Text File**: Upload a .txt file for comparison
3. **Compare Texts**: Click "Compare Texts" to see differences
4. **View Results**: See detailed comparison results with differences highlighted

## API Endpoints

- `POST /extract_text` - Extract text from website URL
- `POST /upload_file` - Upload text file
- `POST /compare_texts` - Compare two texts

## Technologies Used

- **Backend**: Flask (Python)
- **Web Scraping**: BeautifulSoup4, Requests
- **Frontend**: HTML, CSS, JavaScript
- **Text Processing**: Regular Expressions, Difflib

## Deployment

This application is designed to be deployed on Render.com:

1. Connect your GitHub repository to Render
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python app.py`
4. Deploy!

## License

MIT License