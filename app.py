# Add prompts for design analysis
DESIGN_ANALYSIS_PROMPT = """
# Role
You are a Design and Visual Communication Expert specializing in evaluating pitch deck visuals and design elements.

# Task
Analyze the presentation text provided below and infer what design and visual elements are likely present based on the content. Even though you can't directly see the images, you can make educated evaluations based on:

1. References to visual elements (charts, graphs, images, diagrams)
2. The structure and flow of information
3. Mentions of branding, colors, or visual elements
4. Layout descriptions or implied formatting

# Output Format
Provide your evaluation in these sections:
1. "Design Elements Analysis": Assessment of likely visual elements and their effectiveness
2. "Visual Branding": Evaluation of brand consistency and visual identity
3. "Design Recommendations": Specific suggestions to improve the visual presentation in:
   - Slide layouts
   - Color scheme
   - Typography
   - Charts and diagrams
   - Image selection
   - Visual storytelling

Format your recommendations as:
A: "This appears well-designed because..." (inferred from the content)
B: "Consider improving this by..."

# Pitch Deck Content
{pitch_deck_text}
"""

# Function to display evaluation results in tabs
def display_evaluation_results(results):
    import streamlit as st
import os
import tempfile
import anthropic
from PyPDF2 import PdfReader
from pathlib import Path
import json
import time
import pandas as pd
import base64
import sys
import inspect

# This MUST be the first Streamlit command
st.set_page_config(
    page_title="Pitch Deck Evaluator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Debug information about the Anthropic library
debug_mode = False
if debug_mode:
    # This is safe to run after st.set_page_config
    st.write(f"Anthropic version: {anthropic.__version__ if hasattr(anthropic, '__version__') else 'unknown'}")
    st.write(f"Anthropic module path: {inspect.getfile(anthropic)}")
    st.write(f"Available Anthropic classes: {dir(anthropic)}")

# Custom CSS for better UI with light/dark mode support
def add_custom_css():
    st.markdown("""
    <style>
        /* Base styles for both light and dark mode */
        .main {
            padding: 2rem;
        }
        .block-container {
            max-width: 1200px;
            padding-top: 1rem;
        }
        
        /* Typography - will be overridden in dark/light specific styles */
        h1, h2, h3, h4, h5, h6 {
            font-weight: 600;
            margin-bottom: 1rem;
        }
        p, li, div {
            line-height: 1.6;
        }
        
        /* Inputs and Forms - generic styles */
        .stTextInput input, 
        .stFileUploader button {
            border-radius: 4px !important;
        }
        
        /* Buttons - generic styles */
        .stButton button {
            border: none !important;
            font-weight: 500 !important;
            padding: 0.5rem 1.5rem !important;
            border-radius: 4px !important;
            transition: background-color 0.3s ease !important;
        }
        
        /* Tabs - generic styles */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0px;
            padding-bottom: 0px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 4px 4px 0px 0px;
            padding: 10px 16px;
            height: auto;
            font-weight: 500;
            font-size: 0.9rem;
            margin-right: 4px;
        }
        .stTabs [data-baseweb="tab-panel"] {
            padding: 20px 5px;
        }
        
        /* Custom card - generic styles */
        .custom-card {
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 25px;
        }
        
        /* Highlight and recommendation - generic styles */
        .highlight {
            padding: 16px;
            border-radius: 6px;
            margin: 16px 0;
        }
        .recommendation {
            padding-left: 15px;
            margin: 16px 0;
        }
        
        /* Tables - generic styles */
        table {
            border-collapse: collapse;
            margin: 20px 0;
            width: 100%;
        }
        th {
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
        }
        td {
            padding: 12px 16px;
        }
        
        /* Expanders - generic styles */
        .streamlit-expanderHeader {
            border-radius: 6px;
            padding: 10px 15px;
            font-weight: 600;
        }
        .streamlit-expanderContent {
            border-top: none;
            border-radius: 0 0 6px 6px;
            padding: 15px;
        }
        
        /* Light mode specific styles */
        [data-theme="light"] {
            background-color: #f9fafb;
        }
        [data-theme="light"] h1, 
        [data-theme="light"] h2, 
        [data-theme="light"] h3, 
        [data-theme="light"] h4, 
        [data-theme="light"] h5, 
        [data-theme="light"] h6 {
            color: #1a365d;
        }
        [data-theme="light"] p, 
        [data-theme="light"] li, 
        [data-theme="light"] div {
            color: #333333;
        }
        [data-theme="light"] .stTextInput label, 
        [data-theme="light"] .stTextInput span, 
        [data-theme="light"] .stFileUploader label, 
        [data-theme="light"] .stFileUploader span {
            color: #333333 !important;
        }
        [data-theme="light"] .stTextInput input, 
        [data-theme="light"] .stFileUploader button {
            color: #333333 !important;
            background-color: #ffffff !important;
            border-color: #cfd7df !important;
        }
        [data-theme="light"] .stButton button {
            background-color: #2a70ba !important;
            color: white !important;
        }
        [data-theme="light"] .stButton button:hover {
            background-color: #1a5ba6 !important;
        }
        [data-theme="light"] .stTabs [data-baseweb="tab-list"] {
            border-bottom: 1px solid #e2e8f0;
        }
        [data-theme="light"] .stTabs [data-baseweb="tab"] {
            background-color: #f8fafc;
            color: #475569;
            border: 1px solid #e2e8f0;
            border-bottom: none;
        }
        [data-theme="light"] .stTabs [aria-selected="true"] {
            background-color: #2a70ba !important;
            color: white !important;
            border-color: #2a70ba !important;
        }
        [data-theme="light"] .custom-card {
            background-color: white;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            color: #333333;
            border: 1px solid #e5e7eb;
        }
        [data-theme="light"] .highlight {
            background-color: #f0f7ff;
            color: #333333;
            border: 1px solid #d1e2ff;
        }
        [data-theme="light"] .positive {
            color: #047857;
        }
        [data-theme="light"] .negative {
            color: #b91c1c;
        }
        [data-theme="light"] .stProgress .st-ey {
            background-color: #2a70ba;
        }
        [data-theme="light"] .score-pill {
            background-color: #2a70ba;
            color: white;
        }
        [data-theme="light"] .recommendation {
            border-left: 4px solid #2a70ba;
            color: #333333;
        }
        [data-theme="light"] .stStatus {
            background-color: white;
            border: 1px solid #e5e7eb;
        }
        [data-theme="light"] .stStatus div, 
        [data-theme="light"] .stStatus p, 
        [data-theme="light"] .stStatus span {
            color: #333333 !important;
        }
        [data-theme="light"] table {
            color: #333333;
            border: 1px solid #e5e7eb;
        }
        [data-theme="light"] th {
            background-color: #f0f7ff;
            color: #1a365d;
            border: 1px solid #d1e2ff;
        }
        [data-theme="light"] td {
            color: #333333;
            border: 1px solid #e5e7eb;
        }
        [data-theme="light"] .streamlit-expanderHeader {
            background-color: #f0f7ff;
            color: #1a365d !important;
        }
        [data-theme="light"] .streamlit-expanderContent {
            background-color: white;
            color: #333333;
            border: 1px solid #e5e7eb;
        }
        [data-theme="light"] .stMarkdown {
            color: #333333;
        }
        
        /* Dark mode specific styles */
        [data-theme="dark"] {
            background-color: #1e1e1e;
        }
        [data-theme="dark"] h1, 
        [data-theme="dark"] h2, 
        [data-theme="dark"] h3, 
        [data-theme="dark"] h4, 
        [data-theme="dark"] h5, 
        [data-theme="dark"] h6 {
            color: #81b3ff;
        }
        [data-theme="dark"] p, 
        [data-theme="dark"] li, 
        [data-theme="dark"] div {
            color: #e0e0e0;
        }
        [data-theme="dark"] .stTextInput label, 
        [data-theme="dark"] .stTextInput span, 
        [data-theme="dark"] .stFileUploader label, 
        [data-theme="dark"] .stFileUploader span {
            color: #e0e0e0 !important;
        }
        [data-theme="dark"] .stTextInput input, 
        [data-theme="dark"] .stFileUploader button {
            color: #e0e0e0 !important;
            background-color: #2d2d2d !important;
            border-color: #555555 !important;
        }
        [data-theme="dark"] .stButton button {
            background-color: #4d8bdd !important;
            color: white !important;
        }
        [data-theme="dark"] .stButton button:hover {
            background-color: #5d9bef !important;
        }
        [data-theme="dark"] .stTabs [data-baseweb="tab-list"] {
            border-bottom: 1px solid #444444;
        }
        [data-theme="dark"] .stTabs [data-baseweb="tab"] {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #444444;
            border-bottom: none;
        }
        [data-theme="dark"] .stTabs [aria-selected="true"] {
            background-color: #4d8bdd !important;
            color: white !important;
            border-color: #4d8bdd !important;
        }
        [data-theme="dark"] .custom-card {
            background-color: #2d2d2d;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
            color: #e0e0e0;
            border: 1px solid #444444;
        }
        [data-theme="dark"] .highlight {
            background-color: #2d3748;
            color: #e0e0e0;
            border: 1px solid #4a5568;
        }
        [data-theme="dark"] .positive {
            color: #68d391;
        }
        [data-theme="dark"] .negative {
            color: #fc8181;
        }
        [data-theme="dark"] .stProgress .st-ey {
            background-color: #4d8bdd;
        }
        [data-theme="dark"] .score-pill {
            background-color: #4d8bdd;
            color: white;
        }
        [data-theme="dark"] .recommendation {
            border-left: 4px solid #4d8bdd;
            color: #e0e0e0;
        }
        [data-theme="dark"] .stStatus {
            background-color: #2d2d2d;
            border: 1px solid #444444;
        }
        [data-theme="dark"] .stStatus div, 
        [data-theme="dark"] .stStatus p, 
        [data-theme="dark"] .stStatus span {
            color: #e0e0e0 !important;
        }
        [data-theme="dark"] table {
            color: #e0e0e0;
            border: 1px solid #444444;
        }
        [data-theme="dark"] th {
            background-color: #2d3748;
            color: #81b3ff;
            border: 1px solid #4a5568;
        }
        [data-theme="dark"] td {
            color: #e0e0e0;
            border: 1px solid #444444;
        }
        [data-theme="dark"] .streamlit-expanderHeader {
            background-color: #2d3748;
            color: #81b3ff !important;
        }
        [data-theme="dark"] .streamlit-expanderContent {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #444444;
        }
        [data-theme="dark"] .stMarkdown {
            color: #e0e0e0;
        }
        
        /* Sidebar styles - need special handling for dark mode */
        [data-testid="stSidebar"] {
            background-color: #1a365d;
            padding-top: 1.5rem;
        }
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3, 
        [data-testid="stSidebar"] h4, 
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] a,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] div {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] .stMarkdown {
            margin-bottom: 1.5rem;
        }
        [data-testid="stSidebar"] [data-testid="stImage"] {
            margin-bottom: 1rem;
        }
        [data-testid="stSidebar"] h1 {
            font-size: 1.8rem;
            margin-bottom: 0.8rem;
            padding-bottom: 0.8rem;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }
        [data-testid="stSidebar"] hr {
            margin: 1.5rem 0;
            border-color: rgba(255,255,255,0.1);
        }
        [data-testid="stSidebar"] .streamlit-expanderHeader {
            background-color: #2a5082;
            color: white !important;
            border: none;
        }
        [data-testid="stSidebar"] .streamlit-expanderContent {
            background-color: #1a365d;
            border: none;
            padding: 1px 15px 15px 15px;
        }
        [data-testid="stSidebar"] .streamlit-expanderContent p,
        [data-testid="stSidebar"] .streamlit-expanderContent li {
            color: white !important;
        }
        [data-testid="stSidebar"] .stExpander svg {
            fill: white;
        }
    </style>
    """, unsafe_allow_html=True)

add_custom_css()

# Now we can have debug info after the page config
debug_mode = False

if debug_mode:
    st.write(f"Python version: {sys.version}")
    st.write(f"Anthropic version: {anthropic.__version__}")
    st.write(f"Working directory: {os.getcwd()}")

# Create Anthropic client
@st.cache_resource
def get_anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["ANTHROPIC_API_KEY"]
        except Exception as e:
            if debug_mode:
                st.error(f"Error accessing secrets: {str(e)}")
            api_key = None
    
    if not api_key:
        st.error("ANTHROPIC_API_KEY not found. Please set it in your environment variables or Streamlit secrets.")
        if debug_mode:
            st.write("Debug info: Available secrets keys:", list(st.secrets.keys()) if hasattr(st.secrets, "keys") else "No secrets accessible")
        st.stop()
    
    # Initialize the client with just the API key to avoid compatibility issues
    try:
        # First try the simpler initialization that works with newer versions
        return anthropic.Anthropic(api_key=api_key)
    except TypeError:
        # If that fails, try with the older API
        try:
            return anthropic.Client(api_key=api_key)
        except Exception as e:
            st.error(f"Could not initialize Anthropic client (older method): {str(e)}")
            raise

try:
    client = get_anthropic_client()
    if debug_mode:
        st.write("Anthropic client initialized successfully")
except Exception as e:
    st.error(f"Failed to initialize Anthropic client: {str(e)}")
    st.stop()

# Extract text from various presentation file formats
def extract_text_from_file(uploaded_file):
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    if file_extension == 'pdf':
        return extract_text_from_pdf(uploaded_file)
    elif file_extension in ['ppt', 'pptx']:
        return extract_text_from_pptx(uploaded_file)
    elif file_extension in ['doc', 'docx']:
        return extract_text_from_docx(uploaded_file)
    else:
        st.error(f"Unsupported file format: .{file_extension}")
        return None

# Extract text from PDF file
def extract_text_from_pdf(pdf_file):
    temp_dir = tempfile.TemporaryDirectory()
    temp_path = Path(temp_dir.name) / "pitch_deck.pdf"
    
    with open(temp_path, "wb") as f:
        f.write(pdf_file.getvalue())
    
    pdf_reader = PdfReader(temp_path)
    text = ""
    
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n\n"
    
    temp_dir.cleanup()
    return text

# Extract text from PowerPoint file
def extract_text_from_pptx(pptx_file):
    try:
        import pptx
        
        temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(temp_dir.name) / "pitch_deck.pptx"
        
        with open(temp_path, "wb") as f:
            f.write(pptx_file.getvalue())
        
        presentation = pptx.Presentation(temp_path)
        text = ""
        
        for slide in presentation.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
            text += "\n\n"
        
        temp_dir.cleanup()
        return text
    except ImportError:
        st.error("Please install python-pptx: pip install python-pptx")
        return None

# Extract text from Word document
def extract_text_from_docx(docx_file):
    try:
        import docx
        
        temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(temp_dir.name) / "pitch_deck.docx"
        
        with open(temp_path, "wb") as f:
            f.write(docx_file.getvalue())
        
        doc = docx.Document(temp_path)
        text = ""
        
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        temp_dir.cleanup()
        return text
    except ImportError:
        st.error("Please install python-docx: pip install python-docx")
        return None

# Constants for prompts
STORY_PROMPT = """
# Role
You are a Startup Pitch Evaluator with expertise in storytelling and pitch deck evaluation.

# Task
Analyze the following pitch deck and identify the story it tells. Focus on the customer's problem, the solution, and their journey.

If there is no clear story, explain this and suggest a customer story for the pitch.

# Output Format
Provide your response in two sections:
1. "Story Analysis": A brief summary of the story told in the pitch (or lack thereof)
2. "Storytelling Recommendations": Creative recommendations for improving the storytelling based on three approaches:
   - The Hero's Journey
   - The Customer's Tale
   - The Industry's Point of View

Format your recommendations as:
A: "This is good because..." 
B: "I suggest you can improve this by..."

# Pitch Deck Content
{pitch_deck_text}
"""

STARTUP_STAGE_PROMPT = """
# Role
You are a Startup Stage Evaluator with expertise in identifying a venture's growth stage.

# Task
Analyze the following pitch deck and identify which of these startup stages the venture is at:
- Ideation: Conceptualization of core idea, defining business model, target audience, and potential solutions
- Minimum Viable Category (MVC): Identified a unique market category to potentially dominate, outlined problem, audience, and market type
- Initial Product Release (IPR): Launch of first product/service, often as beta for early adopters
- Minimum Viable Product (MVP): Product with just enough features to satisfy early customers and provide feedback
- Minimum Viable Repeatability (MVR): Consistently delivering to target market, demonstrating repeatable business model and scalability potential

# Output Format
Provide your response in three sections:
1. "Current Stage": State which stage the startup is at and justify with specific evidence from the pitch deck
2. "Stage Definition": Provide the definition of the identified stage
3. "Next Stage Planning": Explain the next immediate stage they should aim for and how to get there

# Pitch Deck Content
{pitch_deck_text}
"""

MARKET_ENTRY_PROMPT = """
# Role
You are a Market Strategy Expert who specializes in evaluating startup market entry approaches.

# Task
Analyze the following pitch deck and determine:
1. If the startup has clearly identified their most critical customer segment
2. Whether their strategy aligns more with Blue Ocean Strategy or Red Ocean Strategy

Blue Ocean Strategy:
- Creates new, uncontested market space
- Makes competition irrelevant
- Creates and captures new demand
- Breaks the value-cost trade-off
- Achieves differentiation and low cost simultaneously

Red Ocean Strategy:
- Competes in existing market space
- Beats the competition
- Exploits existing demand
- Makes the value-cost trade-off
- Chooses between differentiation or low cost

# Output Format
Provide your response in three sections:
1. "Customer Segment Analysis": Evaluate how well they've identified their critical customer segment
2. "Strategy Classification": Determine if they're using Blue Ocean or Red Ocean strategy with evidence
3. "Market Entry Recommendations": Provide recommendations to sharpen their customer segment focus and strengthen their chosen strategy

# Pitch Deck Content
{pitch_deck_text}
"""

SCORING_RUBRIC_PROMPT = """
# Role
You are a Startup Pitch Evaluator with expertise in assessing ventures at various stages of development.

# Task
Based on the following pitch deck, complete the appropriate scoring rubric for the startup's identified stage. Score each element from 0-10 (0 = not addressed, 10 = excellent).

# Context
The startup appears to be at the {startup_stage} stage based on previous analysis.

# Output Format
For each criteria in the rubric:
1. Provide specific quotes from the pitch deck that address the criteria
2. Give balanced feedback on what was done well and what needs improvement
3. Offer recommendations in this format:
   A: "This is good because..."
   B: "I suggest you can improve this by..."
   C: "Not addressed. Go out and talk to experts! Try contacting... and ask them..."
   OR
   C: "Not addressed. How does your competitor's business or financial model address..."
4. Assign a score from 0-10

Output should be formatted as a markdown table with these columns:
| Criteria | Question | Quotes | Feedback | Recommendations | Score (0-10) |

End with a total score.

# Rubric for {startup_stage} Stage
{rubric_questions}

# Pitch Deck Content
{pitch_deck_text}
"""

BUSINESS_MODEL_PROMPT = """
# Role
You are a Business Model Expert specializing in startup evaluation.

# Task
Evaluate the following pitch deck using the Business Model Canvas framework. Score each element from 0-10 (0 = not addressed, 10 = excellent).

# Output Format
For each Business Model Canvas element:
1. Extract relevant quotes from the pitch deck
2. Provide balanced feedback on strengths and weaknesses
3. Offer specific recommendations in this format:
   A: "This is good because..."
   B: "I suggest you can improve this by..."
   C: "Not addressed. Go out and talk to experts! Try contacting... and ask them..."
   OR
   C: "Not addressed. How does your competitor's business or financial model address..."
4. Assign a score from 0-10

Output should be formatted as a markdown table with these columns:
| Business Model Canvas Elements | Quotes | Feedback | Recommendations | Score (0-10) |

Include these elements in your evaluation:
- Customer Segments
- Value Propositions
- Channels
- Revenue Streams
- Customer Relationships
- Key Activities
- Key Resources
- Key Partners
- Cost Structure

End with a total score.

# Pitch Deck Content
{pitch_deck_text}
"""

EXPERT_PANEL_PROMPT = """
# Role
You are a Panel Moderator hosting a group of startup experts.

# Task
Simulate feedback from a panel of 5 experts reviewing the following pitch deck:
- Product Expert: Evaluates functionality, usability, design, and product quality
- Revenue Expert: Analyzes monetization strategies, sales, marketing, and revenue potential
- Team Expert: Assesses skills, experience, and cohesiveness of the startup team
- System Expert: Examines operations, processes, and systems for scalability
- Subject Matter Expert: Provides industry-specific insights and market knowledge

# Output Format
For each expert:
1. Identify the evaluation criteria they would focus on
2. Extract relevant quotes from the pitch deck
3. Provide their critical feedback, both positive and negative
4. Offer specific recommendations in this format:
   A: "This is good because..."
   B: "I suggest you can improve this by..."
   C: "Not addressed. Go out and talk to experts! Try contacting... and ask them..."
   OR
   C: "Not addressed. How does your competitor's business or financial model address..."
5. Assign a score from 0-10

Output should be formatted as a markdown table with these columns:
| Expert's Job Title | Evaluation Criteria Used | Quotes | Critique | Recommendations | Score (0-10) |

End with a brief summary of the panel's overall assessment.

# Pitch Deck Content
{pitch_deck_text}
"""

OVERALL_FEEDBACK_PROMPT = """
# Role
You are a Startup Mentor with expertise in pitch deck evaluation and fostering a learning mindset.

# Task
Provide comprehensive feedback on the following pitch deck, synthesizing insights from all previous analyses.

# Context
This startup is at the {startup_stage} stage, using primarily a {market_strategy} strategy.

# Output Format
Offer your feedback in these sections:
1. "Strengths": 3-5 key strengths of the pitch deck
2. "Areas for Improvement": 3-5 specific areas where the pitch could be enhanced
3. "Actionable Next Steps": 3-5 concrete actions the team should take to improve their pitch and business
4. "Motivational Closing": A paragraph that encourages the team to view feedback as an opportunity for growth, emphasizing the learning mindset

Use supportive, constructive language throughout, balancing honesty with encouragement.

# Pitch Deck Content
{pitch_deck_text}
"""

# Rubric questions for each startup stage
RUBRIC_QUESTIONS = {
    "Ideation": [
        "Concept Clarity: How clearly has the startup defined its concept?",
        "Concept Originality: How unique is the startup's concept compared to existing solutions in the market?",
        "Market Research: Has the startup conducted statistically valid market research?",
        "Market Research Quality: How comprehensive and accurate is the market research conducted by the startup?",
        "Market Need: Does the startup's concept address a significant need in the market?",
        "Feature Prioritization: Has the startup prioritized its initial product features based on market research?",
        "Feature Relevance: How relevant are the startup's initial product features to the target market?",
        "Ideation Process: How systematic and thorough was the startup's ideation process?",
        "Persuasiveness: How persuasive is the startup in presenting its concept and market research?",
        "Scalability: Does the startup's concept have the potential to scale in the market?"
    ],
    "Minimum Viable Category (MVC)": [
        "Category Understanding: How well does the startup understand the market category it intends to define or redefine?",
        "Category Thesis: Does the startup have a well-formed thesis regarding the market category?",
        "Thesis Clarity: How clear and concise is the startup's thesis regarding the market category?",
        "Messaging Matrix: Does the startup have a well-thought-out messaging matrix?",
        "Messaging Matrix Relevance: How relevant is the startup's messaging matrix to the market category?",
        "Messaging Matrix Persuasiveness: How persuasive is the startup's messaging matrix?",
        "Market Trends: Is the startup aware of the current trends and dynamics of the market category?",
        "Competitive Landscape: Does the startup understand the competitive landscape of the market category?",
        "Category Potential: Does the startup recognize the potential growth and opportunities in the market category?",
        "Category Strategy: Does the startup have a clear strategy for defining or redefining the market category?"
    ],
    "Initial Product Release (IPR)": [
        "Product Quality: What is the quality of the startup's first publicly deployed product iteration?",
        "MVP Development: Has the startup developed a Minimum Viable Product (MVP)?",
        "MVP Features: Does the MVP include the essential features that address the needs of the target market?",
        "Customer Validation: Is the startup seeking customer validation metrics for its MVP?",
        "Customer Feedback: How is the startup collecting and incorporating customer feedback into its product development?",
        "Product Usability: How user-friendly is the startup's product?",
        "Product Stability: How stable and reliable is the startup's product?",
        "Product Scalability: Does the startup's product have the potential to scale?",
        "Product Market Fit: How well does the startup's product fit into the market it is targeting?",
        "Product Innovation: How innovative is the startup's product compared to existing solutions in the market?"
    ],
    "Minimum Viable Product (MVP)": [
        "MVP Quality: What is the quality of the startup's MVP?",
        "User Feedback: Has the startup received positive feedback from at least 80% of polled users?",
        "User Engagement: How engaged are the users with the startup's MVP?",
        "User Endorsement: Do the users actively use and endorse the startup's product?",
        "MVP Features: Does the MVP include the essential features that address the needs of the target market?",
        "MVP Usability: How user-friendly is the startup's MVP?",
        "MVP Stability: How stable and reliable is the startup's MVP?",
        "MVP Scalability: Does the startup's MVP have the potential to scale?",
        "MVP Innovation: How innovative is the startup's MVP compared to existing solutions in the market?",
        "MVP Market Fit: How well does the startup's MVP fit into the market it is targeting?"
    ],
    "Minimum Viable Repeatability (MVR)": [
        "Customer Acquisition Understanding: How well does the startup understand customer acquisition?",
        "Product Positioning: How effectively has the startup positioned its product in the market?",
        "Reference Customers: Does the startup have a few reference customers who can vouch for its product?",
        "Revenue Generation: Is the startup generating about $2M in Annual Recurring Revenue (ARR)?",
        "Customer Retention: How successful is the startup in retaining its customers?",
        "Customer Acquisition Cost: Is the startup's Customer Acquisition Cost (CAC) sustainable and scalable?",
        "Revenue Growth: Is the startup showing consistent growth in its revenue?",
        "Market Penetration: How successful is the startup in penetrating its target market?",
        "Sales and Marketing Strategy: Does the startup have an effective sales and marketing strategy to acquire and retain customers?",
        "Product-Market Fit: How well does the startup's product fit the needs of its target market?"
    ]
}

# Function to call Claude API
def call_claude_api(prompt, max_tokens=4000):
    try:
        # Check if we're using the newer API (Anthropic 0.7.0+)
        if hasattr(client, 'messages'):
            message = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        # Otherwise use the older API
        else:
            response = client.completion(
                prompt=f"\n\nHuman: {prompt}\n\nAssistant:",
                model="claude-3-5-sonnet-20240620",
                max_tokens_to_sample=max_tokens,
                stop_sequences=["\n\nHuman:"]
            )
            return response.completion
    except Exception as e:
        st.error(f"Error calling Claude API: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None

# Function to create and evaluate a pitch deck
def evaluate_pitch_deck(pitch_deck_text, has_visual_elements=False):
    st.session_state.evaluation_results = {}
    
    # Set up progress tracking
    progress_bar = st.progress(0)
    status_container = st.empty()
    
    try:
        # Initialize evaluation stages and their weights
        stages = [
            {"name": "Identifying startup stage", "weight": 15, "key": "startup_stage", "prompt_func": lambda: STARTUP_STAGE_PROMPT.format(pitch_deck_text=pitch_deck_text)},
            {"name": "Analyzing storytelling elements", "weight": 15, "key": "story", "prompt_func": lambda: STORY_PROMPT.format(pitch_deck_text=pitch_deck_text)},
            {"name": "Evaluating market entry strategy", "weight": 15, "key": "market_entry", "prompt_func": lambda: MARKET_ENTRY_PROMPT.format(pitch_deck_text=pitch_deck_text)},
        ]
        
        # Track progress
        completed_weight = 0
        total_stages = len(stages) + 3  # +3 for the scoring, business model, and expert panel stages which have dynamic prompts
        
        # Process the initial stages
        startup_stage = "Ideation"  # Default value
        market_strategy = "Red Ocean"  # Default value
        
        for i, stage in enumerate(stages):
            status_container.info(f"**{stage['name']}...**")
            
            # Call the API with the appropriate prompt
            stage_prompt = stage["prompt_func"]()
            stage_analysis = call_claude_api(stage_prompt)
            
            if not stage_analysis:
                status_container.error(f"Failed to get {stage['name'].lower()} analysis. Please try again.")
                return None
                
            st.session_state.evaluation_results[stage["key"]] = stage_analysis
            
            # Extract metadata from results if needed
            if stage["key"] == "startup_stage":
                lines = stage_analysis.split('\n')
                for line in lines:
                    if "Current Stage:" in line:
                        parts = line.split(":")
                        if len(parts) > 1:
                            stage_part = parts[1].strip()
                            if "Ideation" in stage_part:
                                startup_stage = "Ideation"
                            elif "Minimum Viable Category" in stage_part or "MVC" in stage_part:
                                startup_stage = "Minimum Viable Category (MVC)"
                            elif "Initial Product Release" in stage_part or "IPR" in stage_part:
                                startup_stage = "Initial Product Release (IPR)"
                            elif "Minimum Viable Product" in stage_part or "MVP" in stage_part:
                                startup_stage = "Minimum Viable Product (MVP)"
                            elif "Minimum Viable Repeatability" in stage_part or "MVR" in stage_part:
                                startup_stage = "Minimum Viable Repeatability (MVR)"
                        break
            
            if stage["key"] == "market_entry":
                lines = stage_analysis.split('\n')
                for line in lines:
                    if "Blue Ocean" in line:
                        market_strategy = "Blue Ocean"
                        break
            
            # Update progress
            completed_weight += stage["weight"]
            progress_bar.progress(completed_weight)
        
        # Apply scoring rubric
        status_container.info("**Applying scoring rubric...**")
        rubric_questions = "\n".join([f"- {q}" for q in RUBRIC_QUESTIONS.get(startup_stage, RUBRIC_QUESTIONS["Ideation"])])
        scoring_prompt = SCORING_RUBRIC_PROMPT.format(
            startup_stage=startup_stage,
            rubric_questions=rubric_questions,
            pitch_deck_text=pitch_deck_text
        )
        scoring_analysis = call_claude_api(scoring_prompt, max_tokens=6000)
        
        if not scoring_analysis:
            status_container.error("Failed to get scoring analysis. Please try again.")
            return None
            
        st.session_state.evaluation_results["scoring"] = scoring_analysis
        
        # Update progress
        completed_weight += 20  # Weight for scoring
        progress_bar.progress(completed_weight)
        
        # Evaluate business model
        status_container.info("**Evaluating business model...**")
        business_model_prompt = BUSINESS_MODEL_PROMPT.format(pitch_deck_text=pitch_deck_text)
        business_model_analysis = call_claude_api(business_model_prompt, max_tokens=6000)
        
        if not business_model_analysis:
            status_container.error("Failed to get business model analysis. Please try again.")
            return None
            
        st.session_state.evaluation_results["business_model"] = business_model_analysis
        
        # Update progress
        completed_weight += 15  # Weight for business model
        progress_bar.progress(completed_weight)
        
        # Get expert panel feedback
        status_container.info("**Gathering expert panel feedback...**")
        expert_panel_prompt = EXPERT_PANEL_PROMPT.format(pitch_deck_text=pitch_deck_text)
        expert_panel_analysis = call_claude_api(expert_panel_prompt, max_tokens=6000)
        
        if not expert_panel_analysis:
            status_container.error("Failed to get expert panel feedback. Please try again.")
            return None
            
        st.session_state.evaluation_results["expert_panel"] = expert_panel_analysis
        
        # Update progress
        completed_weight += 15  # Weight for expert panel
        progress_bar.progress(completed_weight)
        
        # Add visual design analysis if applicable
        if has_visual_elements:
            status_container.info("**Analyzing visual design elements...**")
            design_prompt = DESIGN_ANALYSIS_PROMPT.format(pitch_deck_text=pitch_deck_text)
            design_analysis = call_claude_api(design_prompt)
            
            if design_analysis:
                st.session_state.evaluation_results["design"] = design_analysis
        
        # Generate overall feedback
        status_container.info("**Generating overall feedback...**")
        overall_feedback_prompt = OVERALL_FEEDBACK_PROMPT.format(
            startup_stage=startup_stage,
            market_strategy=market_strategy,
            pitch_deck_text=pitch_deck_text
        )
        overall_feedback = call_claude_api(overall_feedback_prompt)
        
        if not overall_feedback:
            status_container.error("Failed to get overall feedback. Please try again.")
            return None
            
        st.session_state.evaluation_results["overall_feedback"] = overall_feedback
        
        # Complete the progress bar
        progress_bar.progress(100)
        status_container.success("**Analysis complete!**")
        
        # Use st.rerun() instead of the deprecated st.experimental_rerun()
        try:
            st.rerun()
        except Exception as e:
            # For backwards compatibility with older Streamlit versions
            try:
                st.experimental_rerun()
            except Exception as e:
                # If both fail, just return the results - the page will update on the next interaction
                st.success("Analysis complete! Please click on the tabs to view your evaluation.")
        
    except Exception as e:
        status_container.error(f"An error occurred during evaluation: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
    
    return st.session_state.evaluation_results

# Function to display evaluation results in tabs
def display_evaluation_results(results):
    startup_name = st.session_state.get("startup_name", "Your Startup")
    
    # Use the startup name in the title if provided, otherwise use a generic title
    if startup_name and startup_name.strip() != "":
        st.markdown(f"<h1 style='color: #1a365d; margin-bottom: 25px;'>Pitch Deck Evaluation</h1>", unsafe_allow_html=True)
    else:
        st.markdown("<h1 style='color: #1a365d; margin-bottom: 25px;'>Pitch Deck Evaluation</h1>", unsafe_allow_html=True)
    
    # Create tabs for each evaluation section with better icons
    tabs = []
    
    # Build the tab list based on available results
    tab_definitions = [
        {"icon": "📖", "name": "Story Analysis", "key": "story"},
        {"icon": "🚀", "name": "Startup Stage", "key": "startup_stage"},
        {"icon": "🎯", "name": "Market Entry", "key": "market_entry"},
        {"icon": "📊", "name": "Scoring Rubric", "key": "scoring"},
        {"icon": "💼", "name": "Business Model", "key": "business_model"},
        {"icon": "👥", "name": "Expert Panel", "key": "expert_panel"},
        {"icon": "🎨", "name": "Design Analysis", "key": "design"},
        {"icon": "📝", "name": "Overall Feedback", "key": "overall_feedback"}
    ]
    
    # Filter tabs to include only those with results
    tab_labels = []
    available_tabs = []
    for tab in tab_definitions:
        if tab["key"] in results:
            tab_labels.append(f"{tab['icon']} {tab['name']}")
            available_tabs.append(tab)
    
    # Create the tabs
    tabs = st.tabs(tab_labels)
    
    # Populate tabs with content
    for i, tab in enumerate(available_tabs):
        with tabs[i]:
            st.markdown(f"<h2 style='color: #1a365d; margin-top: 10px;'>{tab['name']}</h2>", unsafe_allow_html=True)
            st.markdown(results[tab["key"]])

# UI for the app
def main():
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/data-quality.png", width=80)
        st.title("PitchMe")
        st.markdown("Upload your pitch deck to get expert evaluation on your startup's presentation.")
        
        # About section
        with st.expander("ℹ️ About this app"):
            st.markdown("""
            This app uses AI to evaluate your pitch deck from multiple angles:
            - Storytelling effectiveness
            - Startup stage identification
            - Market entry strategy analysis
            - Detailed scoring based on your stage
            - Business model canvas evaluation
            - Expert panel feedback
            - Overall recommendations
            
            **The evaluation is powered by Claude 3.5 Sonnet**, an advanced AI model by Anthropic.
            """)
        
        # Instructions
        with st.expander("📋 How to use"):
            st.markdown("""
            1. Enter your startup's name (optional)
            2. Upload your pitch deck (PDF, PPT, PPTX, DOC, or DOCX)
            3. Click "Evaluate Pitch Deck"
            4. Review the detailed analysis across various tabs
            5. Use the feedback to improve your pitch deck
            """)
        
        st.divider()
        st.markdown("<div style='text-align: center; font-size: 0.9rem; opacity: 0.8; margin-top: 20px;'>Made by ProtoBots.ai</div>", unsafe_allow_html=True)
    
    # Main content
    if "evaluation_results" not in st.session_state:
        # Initial state - show upload form
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("<h1 style='color: #1a365d; margin-bottom: 20px;'>PitchMe</h1>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 1.1rem; margin-bottom: 25px;'>Get expert AI-powered feedback on your pitch deck to impress investors and secure funding.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.markdown("<h3 style='color: #1a365d; margin-bottom: 20px;'>Upload Your Pitch Deck</h3>", unsafe_allow_html=True)
            st.session_state.startup_name = st.text_input("Startup Name (Optional)", "")
            
            uploaded_file = st.file_uploader(
                "Upload your pitch deck", 
                type=["pdf", "ppt", "pptx", "doc", "docx"]
            )
            
            analyze_visuals = st.checkbox("Also analyze visual design elements", value=True)
            
            if uploaded_file is not None:
                file_type = uploaded_file.name.split('.')[-1].lower()
                st.write(f"File type detected: .{file_type}")
                
                if st.button("Evaluate Pitch Deck", type="primary", use_container_width=True):
                    with st.spinner("Extracting text from your pitch deck..."):
                        pitch_deck_text = extract_text_from_file(uploaded_file)
                        if not pitch_deck_text or len(pitch_deck_text) < 100:
                            st.error("Could not extract sufficient text from the file. Please make sure your file has textual content and not just images.")
                        else:
                            evaluate_pitch_deck(pitch_deck_text, has_visual_elements=analyze_visuals)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.markdown("<h3 style='color: #1a365d; margin-bottom: 15px;'>What You'll Get</h3>", unsafe_allow_html=True)
            st.markdown("""
            - 📖 **Story Analysis**
            - 🚀 **Startup Stage Identification**
            - 🎯 **Market Entry Strategy Assessment**
            - 📊 **Detailed Scoring Rubric**
            - 💼 **Business Model Evaluation**
            - 👥 **Expert Panel Feedback**
            - 📝 **Actionable Recommendations**
            """)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.markdown("<h3 style='color: #1a365d; margin-bottom: 15px;'>Supported Formats</h3>", unsafe_allow_html=True)
            st.markdown("""
            We support multiple presentation formats:
            
            - **PDF** (.pdf)
            - **PowerPoint** (.ppt, .pptx)
            - **Word Documents** (.doc, .docx)
            """)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.markdown("<h3 style='color: #1a365d; margin-bottom: 15px;'>Why It Matters</h3>", unsafe_allow_html=True)
            st.markdown("""
            A compelling pitch deck is crucial for securing investment. Our AI evaluator helps you:
            
            - Identify weaknesses before investors do
            - Strengthen your narrative and positioning
            - Align with investor expectations
            - Prepare for tough questions
            """)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        # Display evaluation results
        display_evaluation_results(st.session_state.evaluation_results)
        
        # Add a button to start over
        if st.button("Evaluate Another Pitch Deck", type="primary"):
            # Clear the session state and rerun the script
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            try:
                st.rerun()
            except Exception as e:
                try:
                    st.experimental_rerun()
                except Exception as e:
                    st.info("Please refresh the page to evaluate another pitch deck.")
                    st.stop()

if __name__ == "__main__":
    main()
