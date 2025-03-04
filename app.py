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

# Set page configuration
st.set_page_config(
    page_title="Pitch Deck Evaluator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
def add_custom_css():
    st.markdown("""
    <style>
        .main {
            padding: 2rem;
        }
        .stApp {
            background-color: #f8f9fa;
        }
        .block-container {
            max-width: 1200px;
            padding-top: 2rem;
        }
        h1, h2, h3 {
            color: #1e3a8a;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #f1f5f9;
            border-radius: 4px 4px 0px 0px;
            padding: 10px 20px;
            height: auto;
        }
        .stTabs [aria-selected="true"] {
            background-color: #3b82f6 !important;
            color: white !important;
        }
        .custom-card {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        .highlight {
            background-color: #e0f2fe;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .positive {
            color: #059669;
            font-weight: 500;
        }
        .negative {
            color: #dc2626;
            font-weight: 500;
        }
        .stProgress .st-ey {
            background-color: #3b82f6;
        }
        .score-pill {
            background-color: #3b82f6;
            color: white;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: bold;
            display: inline-block;
            margin-left: 10px;
        }
        .recommendation {
            border-left: 4px solid #3b82f6;
            padding-left: 15px;
            margin: 10px 0;
        }
    </style>
    """, unsafe_allow_html=True)

add_custom_css()

# Create Anthropic client
@st.cache_resource
def get_anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
    
    if not api_key:
        st.error("ANTHROPIC_API_KEY not found. Please set it in your environment variables or Streamlit secrets.")
        st.stop()
    
    return anthropic.Anthropic(api_key=api_key)

client = get_anthropic_client()

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
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        st.error(f"Error calling Claude API: {str(e)}")
        return None

# Function to create and evaluate a pitch deck
def evaluate_pitch_deck(pitch_deck_text):
    st.session_state.evaluation_results = {}
    
    with st.status("Analyzing your pitch deck...", expanded=True) as status:
        # Determine startup stage
        status.update(label="Identifying startup stage...")
        startup_stage_prompt = STARTUP_STAGE_PROMPT.format(pitch_deck_text=pitch_deck_text)
        startup_stage_analysis = call_claude_api(startup_stage_prompt)
        st.session_state.evaluation_results["startup_stage"] = startup_stage_analysis
        
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
        st.session_state.evaluation_results["story"] = story_analysis
        
        # Evaluate market entry strategy
        status.update(label="Evaluating market entry strategy...")
        market_entry_prompt = MARKET_ENTRY_PROMPT.format(pitch_deck_text=pitch_deck_text)
        market_entry_analysis = call_claude_api(market_entry_prompt)
        st.session_state.evaluation_results["market_entry"] = market_entry_analysis
        
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
        st.session_state.evaluation_results["scoring"] = scoring_analysis
        
        # Evaluate business model
        status.update(label="Evaluating business model...")
        business_model_prompt = BUSINESS_MODEL_PROMPT.format(pitch_deck_text=pitch_deck_text)
        business_model_analysis = call_claude_api(business_model_prompt, max_tokens=6000)
        st.session_state.evaluation_results["business_model"] = business_model_analysis
        
        # Get expert panel feedback
        status.update(label="Gathering expert panel feedback...")
        expert_panel_prompt = EXPERT_PANEL_PROMPT.format(pitch_deck_text=pitch_deck_text)
        expert_panel_analysis = call_claude_api(expert_panel_prompt, max_tokens=6000)
        st.session_state.evaluation_results["expert_panel"] = expert_panel_analysis
        
        # Generate overall feedback
        status.update(label="Generating overall feedback...")
        overall_feedback_prompt = OVERALL_FEEDBACK_PROMPT.format(
            startup_stage=startup_stage,
            market_strategy=market_strategy,
            pitch_deck_text=pitch_deck_text
        )
        overall_feedback = call_claude_api(overall_feedback_prompt)
        st.session_state.evaluation_results["overall_feedback"] = overall_feedback
        
        status.update(label="Analysis complete!", state="complete")
    
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
        st.title("Pitch Deck Evaluator")
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
        st.markdown("Made by Your Company")
    
    # Main content
    if "evaluation_results" not in st.session_state:
        # Initial state - show upload form
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.title("🚀 Startup Pitch Deck Evaluator")
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