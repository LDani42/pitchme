import streamlit as st
import os
import tempfile
import anthropic
from PyPDF2 import PdfReader
from pathlib import Path

# This MUST be the very first Streamlit command
st.set_page_config(
    page_title="PitchMe",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

End with a total score and summary assessment.

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

End with a brief summary of the panel's overall assessment.

# Pitch Deck Content
{pitch_deck_text}
"""

OVERALL_FEEDBACK_PROMPT = """
# Role
You are a Startup Mentor with expertise in pitch deck evaluation and fostering a learning mindset.

# Task
Provide comprehensive feedback on the following pitch deck.

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

# Add CSS for styling
def add_custom_css():
    st.markdown("""
    <style>
        /* Basic styling */
        h1, h2, h3 { color: #1a365d; margin-bottom: 1rem; }
        p, li, div { color: #333333; line-height: 1.6; }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #1a365d;
            padding-top: 1rem;
        }
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3, 
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] a,
        [data-testid="stSidebar"] .stMarkdown {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] h1 {
            font-size: 1.8rem;
            margin-bottom: 0.8rem;
            padding-bottom: 0.8rem;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }
        
        /* Card styling */
        .custom-card {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        
        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0px;
            border-bottom: 1px solid #e2e8f0;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: #f8fafc;
            border-radius: 4px 4px 0px 0px;
            padding: 10px 16px;
            color: #475569;
            font-weight: 500;
            border: 1px solid #e2e8f0;
            border-bottom: none;
            margin-right: 4px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #2a70ba !important;
            color: white !important;
        }
        
        /* Button styling */
        .stButton button {
            background-color: #2a70ba !important;
            color: white !important;
            border: none !important;
            font-weight: 500 !important;
        }
        .stButton button:hover {
            background-color: #1a5ba6 !important;
        }
    </style>
    """, unsafe_allow_html=True)

add_custom_css()

# Create Anthropic client
def get_anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["ANTHROPIC_API_KEY"]
        except Exception as e:
            st.error(f"Error accessing secrets: {str(e)}")
            st.stop()
    
    # Try different initialization methods for compatibility
    try:
        return anthropic.Anthropic(api_key=api_key)
    except Exception as e:
        try:
            return anthropic.Client(api_key=api_key)
        except Exception as e:
            st.error(f"Could not initialize Anthropic client: {str(e)}")
            st.stop()

client = get_anthropic_client()

# Function to call Claude API
def call_claude_api(prompt, max_tokens=4000):
    try:
        # Try newer API first
        if hasattr(client, 'messages'):
            message = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        # Fall back to older API
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
        return None

# Extract text from various file formats
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

# Extract text from PDF
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

# Extract text from PowerPoint
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
        st.error("PowerPoint processing library not available. Please install python-pptx.")
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
        
        for para in doc.paragraphs:
            text += para.text + "\n"
        
        temp_dir.cleanup()
        return text
    except ImportError:
        st.error("Word processing library not available. Please install python-docx.")
        return None

# Function to evaluate the pitch deck
def evaluate_pitch_deck(pitch_deck_text, analyze_design=False):
    results = {}
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Determine how many analyses we'll run
    total_analyses = 6  # Base analyses including business model and expert panel
    if analyze_design:
        total_analyses += 1
    progress_step = 100 / total_analyses
    current_progress = 0
    
    # Story Analysis
    status_text.text("Analyzing story elements...")
    story_prompt = STORY_PROMPT.format(pitch_deck_text=pitch_deck_text)
    story_analysis = call_claude_api(story_prompt)
    if story_analysis:
        results["story"] = story_analysis
        current_progress += progress_step
        progress_bar.progress(int(current_progress))
    else:
        st.error("Failed to analyze story elements.")
        return None
    
    # Startup Stage
    status_text.text("Identifying startup stage...")
    stage_prompt = STARTUP_STAGE_PROMPT.format(pitch_deck_text=pitch_deck_text)
    stage_analysis = call_claude_api(stage_prompt)
    if stage_analysis:
        results["startup_stage"] = stage_analysis
        current_progress += progress_step
        progress_bar.progress(int(current_progress))
    else:
        st.error("Failed to identify startup stage.")
        return None
    
    # Market Entry
    status_text.text("Evaluating market entry strategy...")
    market_prompt = MARKET_ENTRY_PROMPT.format(pitch_deck_text=pitch_deck_text)
    market_analysis = call_claude_api(market_prompt)
    if market_analysis:
        results["market_entry"] = market_analysis
        current_progress += progress_step
        progress_bar.progress(int(current_progress))
    else:
        st.error("Failed to evaluate market entry strategy.")
        return None
    
    # Business Model
    status_text.text("Analyzing business model...")
    business_prompt = BUSINESS_MODEL_PROMPT.format(pitch_deck_text=pitch_deck_text)
    business_analysis = call_claude_api(business_prompt, max_tokens=6000)
    if business_analysis:
        results["business_model"] = business_analysis
        current_progress += progress_step
        progress_bar.progress(int(current_progress))
    else:
        st.error("Failed to analyze business model.")
        return None
    
    # Expert Panel
    status_text.text("Gathering expert panel feedback...")
    expert_prompt = EXPERT_PANEL_PROMPT.format(pitch_deck_text=pitch_deck_text)
    expert_analysis = call_claude_api(expert_prompt, max_tokens=6000)
    if expert_analysis:
        results["expert_panel"] = expert_analysis
        current_progress += progress_step
        progress_bar.progress(int(current_progress))
    else:
        st.error("Failed to gather expert panel feedback.")
        return None
    
    # Design Analysis (optional)
    if analyze_design:
        status_text.text("Analyzing design elements...")
        design_prompt = DESIGN_ANALYSIS_PROMPT.format(pitch_deck_text=pitch_deck_text)
        design_analysis = call_claude_api(design_prompt)
        if design_analysis:
            results["design"] = design_analysis
            current_progress += progress_step
            progress_bar.progress(int(current_progress))
    
    # Overall Feedback
    status_text.text("Generating overall feedback...")
    feedback_prompt = OVERALL_FEEDBACK_PROMPT.format(pitch_deck_text=pitch_deck_text)
    overall_feedback = call_claude_api(feedback_prompt)
    if overall_feedback:
        results["overall_feedback"] = overall_feedback
        current_progress += progress_step
        progress_bar.progress(100)  # Ensure we reach 100%
        status_text.text("Analysis complete!")
    else:
        st.error("Failed to generate overall feedback.")
        return None
    
    return results

# Function to display evaluation results in tabs
def display_evaluation_results(results):
    st.title("Pitch Deck Evaluation")
    
    # Define all possible tabs and their keys
    tab_definitions = [
        {"label": "📖 Story Analysis", "key": "story"},
        {"label": "🚀 Startup Stage", "key": "startup_stage"},
        {"label": "🎯 Market Entry", "key": "market_entry"},
        {"label": "💼 Business Model", "key": "business_model"},
        {"label": "👥 Expert Panel", "key": "expert_panel"},
        {"label": "🎨 Design Analysis", "key": "design"},
        {"label": "📝 Overall Feedback", "key": "overall_feedback"}
    ]
    
    # Filter to include only tabs with results
    available_tabs = [tab for tab in tab_definitions if tab["key"] in results]
    tab_labels = [tab["label"] for tab in available_tabs]
    
    # Create tabs
    tabs = st.tabs(tab_labels)
    
    # Populate each tab with content
    for i, tab in enumerate(available_tabs):
        with tabs[i]:
            st.header(tab["label"].split(" ", 1)[1])  # Remove emoji from header
            st.markdown(results[tab["key"]])

def main():
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/data-quality.png", width=80)
        st.title("PitchMe")
        st.markdown("Upload your pitch deck to get expert evaluation.")
        
        with st.expander("ℹ️ About"):
            st.markdown("""
            This app uses AI to evaluate your pitch deck from multiple angles:
            - Storytelling effectiveness
            - Startup stage identification
            - Market entry strategy analysis
            - Business model canvas evaluation
            - Expert panel feedback
            - Design and visual elements (optional)
            - Overall recommendations
            
            **The evaluation is powered by Claude 3.5 Sonnet**, an advanced AI model by Anthropic.
            """)
        
        with st.expander("📋 How to use"):
            st.markdown("""
            1. Enter your startup's name (optional)
            2. Upload your pitch deck (PDF, PPT, PPTX, DOC, or DOCX)
            3. Select whether to analyze design elements
            4. Click "Evaluate Pitch Deck"
            5. Review the detailed analysis across various tabs
            6. Use the feedback to improve your pitch deck
            """)
        
        st.divider()
        st.markdown("<div style='text-align: center; font-size: 0.9rem; opacity: 0.8; margin-top: 20px;'>Made by ProtoBots.ai</div>", unsafe_allow_html=True)
    
    # Main content area
    if "evaluation_results" not in st.session_state:
        # Initial state - show upload form
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.title("PitchMe")
        st.markdown("Get expert AI-powered feedback on your pitch deck to impress investors and secure funding.")
        st.markdown("</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.header("Upload Your Pitch Deck")
            startup_name = st.text_input("Startup Name (Optional)", "")
            
            uploaded_file = st.file_uploader(
                "Upload your pitch deck", 
                type=["pdf", "ppt", "pptx", "doc", "docx"]
            )
            
            analyze_design = st.checkbox("Also analyze design and visual elements", value=True)
            
            if uploaded_file is not None:
                file_type = uploaded_file.name.split('.')[-1].lower()
                st.write(f"File type detected: .{file_type}")
                
                if st.button("Evaluate Pitch Deck", type="primary", use_container_width=True):
                    pitch_deck_text = extract_text_from_file(uploaded_file)
                    
                    if not pitch_deck_text or len(pitch_deck_text) < 100:
                        st.error("Could not extract sufficient text from the file. Please make sure your file has textual content and not just images.")
                    else:
                        st.session_state.startup_name = startup_name
                        with st.spinner("Analyzing your pitch deck..."):
                            results = evaluate_pitch_deck(pitch_deck_text, analyze_design)
                            if results:
                                st.session_state.evaluation_results = results
                                # Instead of directly calling rerun, just display the results
                                st.success("Analysis complete!")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.header("What You'll Get")
            st.markdown("""
            - 📖 **Story Analysis**
            - 🚀 **Startup Stage Identification**
            - 🎯 **Market Entry Strategy Assessment**
            - 💼 **Business Model Evaluation**
            - 👥 **Expert Panel Feedback**
            - 🎨 **Design Analysis** (optional)
            - 📝 **Actionable Recommendations**
            """)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
            st.header("Supported Formats")
            st.markdown("""
            We support multiple presentation formats:
            
            - **PDF** (.pdf)
            - **PowerPoint** (.ppt, .pptx)
            - **Word Documents** (.doc, .docx)
            """)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        # Display evaluation results
        display_evaluation_results(st.session_state.evaluation_results)
        
        # Add a button to start over
        if st.button("Evaluate Another Pitch Deck", type="primary"):
            # Clear the session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # Don't use rerun, just refresh the page
            st.info("Please refresh the page to evaluate another pitch deck.")

if __name__ == "__main__":
    main()
