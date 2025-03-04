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

# Custom CSS for better UI
def add_custom_css():
    st.markdown("""
    <style>
        /* Main page */
        .main {
            padding: 2rem;
            background-color: #f9fafb;
        }
        .stApp {
            background-color: #f9fafb;
        }
        .block-container {
            max-width: 1200px;
            padding-top: 2rem;
        }
        
        /* Typography */
        h1, h2, h3, h4, h5, h6 {
            color: #1a365d;
            font-weight: 600;
        }
        p, li, div {
            color: #333333;
        }
        
        /* Sidebar */
        .css-1d391kg, .css-12oz5g7 {
            background-color: #1a365d;
        }
        [data-testid="stSidebar"] {
            background-color: #1a365d;
        }
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3, 
        [data-testid="stSidebar"] h4, 
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] a,
        [data-testid="stSidebar"] .stMarkdown {
            color: #ffffff !important;
        }
        
        /* Inputs and Forms */
        .stTextInput label, 
        .stTextInput span, 
        .stFileUploader label, 
        .stFileUploader span {
            color: #333333 !important;
        }
        .stTextInput input, 
        .stFileUploader button {
            color: #333333 !important;
            background-color: #ffffff !important;
            border-color: #cfd7df !important;
        }
        
        /* Buttons */
        .stButton button {
            background-color: #2a70ba !important;
            color: white !important;
            border: none !important;
            font-weight: 500 !important;
        }
        .stButton button:hover {
            background-color: #1a5ba6 !important;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #dfe5ed;
            border-radius: 4px 4px 0px 0px;
            padding: 10px 20px;
            height: auto;
            color: #333333;
        }
        .stTabs [aria-selected="true"] {
            background-color: #2a70ba !important;
            color: white !important;
        }
        
        /* Cards */
        .custom-card {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            margin-bottom: 20px;
            color: #333333;
            border: 1px solid #e5e7eb;
        }
        
        /* Content Elements */
        .highlight {
            background-color: #f0f7ff;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            color: #333333;
            border: 1px solid #d1e2ff;
        }
        .positive {
            color: #047857;
            font-weight: 500;
        }
        .negative {
            color: #b91c1c;
            font-weight: 500;
        }
        
        /* Progress and Status */
        .stProgress .st-ey {
            background-color: #2a70ba;
        }
        .score-pill {
            background-color: #2a70ba;
            color: white;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: bold;
            display: inline-block;
            margin-left: 10px;
        }
        .recommendation {
            border-left: 4px solid #2a70ba;
            padding-left: 15px;
            margin: 10px 0;
            color: #333333;
        }
        
        /* Status elements */
        .stStatus div, .stStatus p, .stStatus span {
            color: #333333 !important;
        }
        
        /* Tables */
        table {
            color: #333333;
            border-collapse: collapse;
        }
        th {
            background-color: #f0f7ff;
            color: #1a365d;
            padding: 8px 12px;
            border: 1px solid #d1e2ff;
        }
        td {
            color: #333333;
            padding: 8px 12px;
            border: 1px solid #e5e7eb;
        }
        
        /* Expanders */
        .streamlit-expanderHeader {
            background-color: #f0f7ff;
            color: #1a365d !important;
            border-radius: 4px;
        }
        .streamlit-expanderContent {
            background-color: white;
            color: #333333;
            border: 1px solid #e5e7eb;
            border-top: none;
            border-radius: 0 0 4px 4px;
        }
        
        /* Markdown */
        .stMarkdown {
            color: #333333;
        }
        
        /* Code blocks */
        .stCodeBlock {
            background-color: #1a1a1a;
        }
        .stCodeBlock code {
            color: #f0f0f0;
        }
        
        /* Sidebar expander */
        [data-testid="stSidebar"] .streamlit-expanderHeader {
            background-color: #2a5082;
            color: white !important;
        }
        [data-testid="stSidebar"] .streamlit-expanderContent {
            background-color: #1a365d;
            border: none;
        }
        [data-testid="stSidebar"] .streamlit-expanderContent p,
        [data-testid="stSidebar"] .streamlit-expanderContent li {
            color: white !important;
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
def evaluate_pitch_deck(pitch_deck_text):
    st.session_state.evaluation_results = {}
    
    with st.status("Analyzing your pitch deck...", expanded=True) as status:
        # Determine startup stage
        status.update(label="Identifying startup stage...")
        startup_stage_prompt = STARTUP_STAGE_PROMPT.format(pitch_deck_text=pitch_deck_text)
        startup_stage_analysis = call_claude_api(startup_stage_prompt)
        
        if not startup_stage_analysis:
            st.error("Failed to get startup stage analysis. Please try again.")
            return None
            
        st.session_state.evaluation_results["startup_stage"] = startup_stage_analysis
        status.update(label="✅ Startup stage identified")
        
        # Extract the stage name for use in other prompts
        lines = startup_stage_analysis.split('\n')
        startup_stage = "Ideation"  # Default value
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
        
        # Analyze the story
        status.update(label="Analyzing storytelling elements...")
        story_prompt = STORY_PROMPT.format(pitch_deck_text=pitch_deck_text)
        story_analysis = call_claude_api(story_prompt)
        
        if not story_analysis:
            st.error("Failed to get story analysis. Please try again.")
            return None
            
        st.session_state.evaluation_results["story"] = story_analysis
        status.update(label="✅ Story analysis complete")
        
        # Evaluate market entry strategy
        status.update(label="Evaluating market entry strategy...")
        market_entry_prompt = MARKET_ENTRY_PROMPT.format(pitch_deck_text=pitch_deck_text)
        market_entry_analysis = call_claude_api(market_entry_prompt)
        
        if not market_entry_analysis:
            st.error("Failed to get market entry analysis. Please try again.")
            return None
            
        st.session_state.evaluation_results["market_entry"] = market_entry_analysis
        status.update(label="✅ Market entry strategy evaluated")
        
        # Extract market strategy for use in overall feedback
        lines = market_entry_analysis.split('\n')
        market_strategy = "Red Ocean"  # Default value
        for line in lines:
            if "Blue Ocean" in line:
                market_strategy = "Blue Ocean"
                break
        
        # Apply scoring rubric
        status.update(label="Applying scoring rubric...")
        rubric_questions = "\n".join([f"- {q}" for q in RUBRIC_QUESTIONS.get(startup_stage, RUBRIC_QUESTIONS["Ideation"])])
        scoring_prompt = SCORING_RUBRIC_PROMPT.format(
            startup_stage=startup_stage,
            rubric_questions=rubric_questions,
            pitch_deck_text=pitch_deck_text
        )
        scoring_analysis = call_claude_api(scoring_prompt, max_tokens=6000)
        
        if not scoring_analysis:
            st.error("Failed to get scoring analysis. Please try again.")
            return None
            
        st.session_state.evaluation_results["scoring"] = scoring_analysis
        status.update(label="✅ Scoring rubric applied")
        
        # Evaluate business model
        status.update(label="Evaluating business model...")
        business_model_prompt = BUSINESS_MODEL_PROMPT.format(pitch_deck_text=pitch_deck_text)
        business_model_analysis = call_claude_api(business_model_prompt, max_tokens=6000)
        
        if not business_model_analysis:
            st.error("Failed to get business model analysis. Please try again.")
            return None
            
        st.session_state.evaluation_results["business_model"] = business_model_analysis
        status.update(label="✅ Business model evaluated")
        
        # Get expert panel feedback
        status.update(label="Gathering expert panel feedback...")
        expert_panel_prompt = EXPERT_PANEL_PROMPT.format(pitch_deck_text=pitch_deck_text)
        expert_panel_analysis = call_claude_api(expert_panel_prompt, max_tokens=6000)
        
        if not expert_panel_analysis:
            st.error("Failed to get expert panel feedback. Please try again.")
            return None
            
        st.session_state.evaluation_results["expert_panel"] = expert_panel_analysis
        status.update(label="✅ Expert panel feedback gathered")
        
        # Generate overall feedback
        status.update(label="Generating overall feedback...")
        overall_feedback_prompt = OVERALL_FEEDBACK_PROMPT.format(
            startup_stage=startup_stage,
            market_strategy=market_strategy,
            pitch_deck_text=pitch_deck_text
        )
        overall_feedback = call_claude_api(overall_feedback_prompt)
        
        if not overall_feedback:
            st.error("Failed to get overall feedback. Please try again.")
            return None
            
        st.session_state.evaluation_results["overall_feedback"] = overall_feedback
        status.update(label="✅ Overall feedback generated")
        
        status.update(label="Analysis complete!", state="complete")
    
    # Force a page refresh to display the results
    st.experimental_rerun()
    
    return st.session_state.evaluation_results

# Function to display evaluation results in tabs
def display_evaluation_results(results):
    startup_name = st.session_state.get("startup_name", "Your Startup")
    st.markdown(f"# Pitch Deck Evaluation for **{startup_name}**")
    
    # Create tabs for each evaluation section
    tabs = st.tabs([
        "📖 Story Analysis", 
        "🚀 Startup Stage", 
        "🎯 Market Entry", 
        "📊 Scoring Rubric", 
        "💼 Business Model", 
        "👥 Expert Panel", 
        "📝 Overall Feedback"
    ])
    
    # Story Analysis Tab
    with tabs[0]:
        st.markdown("## Story Analysis")
        st.markdown(results["story"])
    
    # Startup Stage Tab
    with tabs[1]:
        st.markdown("## Startup Stage Identification")
        st.markdown(results["startup_stage"])
    
    # Market Entry Tab
    with tabs[2]:
        st.markdown("## Market Entry Strategy")
        st.markdown(results["market_entry"])
    
    # Scoring Rubric Tab
    with tabs[3]:
        st.markdown("## Scoring Rubric Assessment")
        st.markdown(results["scoring"])
    
    # Business Model Tab
    with tabs[4]:
        st.markdown("## Business Model Canvas Evaluation")
        st.markdown(results["business_model"])
    
    # Expert Panel Tab
    with tabs[5]:
        st.markdown("## Expert Panel Feedback")
        st.markdown(results["expert_panel"])
    
    # Overall Feedback Tab
    with tabs[6]:
        st.markdown("## Overall Feedback")
        st.markdown(results["overall_feedback"])

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
            2. Upload your pitch deck as a PDF file
            3. Click "Evaluate Pitch Deck"
            4. Review the detailed analysis across various tabs
            5. Use the feedback to improve your pitch deck
            """)
        
        st.divider()
        st.markdown("Made by ProtoBots.ai")
    
    # Main content
    if "evaluation_results" not in st.session_state:
        # Initial state - show upload form
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.title("🚀 PitchMe")
        st.markdown("Get expert AI-powered feedback on your pitch deck to impress investors and secure funding.")
        st.markdown("</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.markdown("### Upload Your Pitch Deck")
            st.session_state.startup_name = st.text_input("Startup Name (Optional)", "")
            uploaded_file = st.file_uploader("Upload your pitch deck (PDF)", type="pdf")
            
            if uploaded_file is not None:
                if st.button("Evaluate Pitch Deck", type="primary", use_container_width=True):
                    with st.spinner("Extracting text from your pitch deck..."):
                        pitch_deck_text = extract_text_from_pdf(uploaded_file)
                        if not pitch_deck_text or len(pitch_deck_text) < 100:
                            st.error("Could not extract sufficient text from the PDF. Please make sure your PDF has text content and not just images.")
                        else:
                            evaluate_pitch_deck(pitch_deck_text)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.markdown("### What You'll Get")
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
            st.markdown("### Why It Matters")
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
            st.experimental_rerun()

if __name__ == "__main__":
    main()
