import streamlit as st
import os
import tempfile
import anthropic
from PyPDF2 import PdfReader
from pathlib import Path
import time
from fpdf import FPDF
from io import BytesIO

# This MUST be the very first Streamlit command
st.set_page_config(
    page_title="PitchMe",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants for prompts
STORY_PROMPT = """
# Role
You are a Startup Pitch Evaluator with expertise in storytelling and pitch deck evaluation.
...
# Pitch Deck Content
{pitch_deck_text}
"""

STARTUP_STAGE_PROMPT = """
# Role
You are a Startup Stage Evaluator with expertise in identifying a venture's growth stage.
...
# Pitch Deck Content
{pitch_deck_text}
"""

MARKET_ENTRY_PROMPT = """
# Role
You are a Market Strategy Expert who specializes in evaluating startup market entry approaches.
...
# Pitch Deck Content
{pitch_deck_text}
"""

BUSINESS_MODEL_PROMPT = """
# Role
You are a Business Model Expert specializing in startup evaluation.
...
# Pitch Deck Content
{pitch_deck_text}
"""

EXPERT_PANEL_PROMPT = """
# Role
You are a Panel Moderator hosting a group of startup experts.
...
# Pitch Deck Content
{pitch_deck_text}
"""

OVERALL_FEEDBACK_PROMPT = """
# Role
You are a Startup Mentor with expertise in pitch deck evaluation and fostering a learning mindset.
...
# Pitch Deck Content
{pitch_deck_text}
"""

DESIGN_ANALYSIS_PROMPT = """
# Role
You are a Design and Visual Communication Expert specializing in evaluating pitch deck visuals and design elements.
...
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
        
        /* Make sure all text in sidebar is white */
        [data-testid="stSidebar"] {
            background-color: #1a365d;
            padding-top: 1rem;
        }
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3, 
        [data-testid="stSidebar"] h4, 
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] a,
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] div,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] li,
        [data-testid="stSidebar"] .streamlit-expanderHeader,
        [data-testid="stSidebar"] .streamlit-expanderContent {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] h1 {
            font-size: 1.8rem;
            margin-bottom: 0.8rem;
            padding-bottom: 0.8rem;
            border-bottom: 1px solid rgba(255,255,255,0.2);
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
            font-weight: bold !important;
        }
        .stButton button:hover {
            background-color: #1a5ba6 !important;
        }
        
        /* Make blockquotes stand out */
        blockquote {
            background-color: #f8f9fa;
            border-left: 5px solid #2a70ba;
            padding: 10px 15px;
            margin: 10px 0;
            color: #333333;
        }
        
        /* Table styling */
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
        }
        th {
            background-color: #edf2f7;
            border: 1px solid #cbd5e0;
            padding: 8px 12px;
            text-align: left;
            color: #1a365d;
        }
        td {
            border: 1px solid #cbd5e0;
            padding: 8px 12px;
        }
        tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        /* Code blocks */
        pre {
            background-color: #f1f5f9;
            border-radius: 6px;
            padding: 16px;
            border: 1px solid #e2e8f0;
            overflow-x: auto;
        }
        
        /* Emoji sizing */
        em {
            font-style: normal;
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
        if hasattr(client, 'messages'):
            message = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
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

def export_results_to_pdf(results):
    pdf = FPDF()
    pdf.add_page()
    import os
    base_path = os.path.dirname(__file__)
    font_path = os.path.join(base_path, "fonts", "DejaVuSans.ttf")
    bold_font_path = os.path.join(base_path, "fonts", "DejaVuSans-Bold.ttf")
    
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.add_font("DejaVu", "B", bold_font_path, uni=True)
    pdf.set_font("DejaVu", size=12)
    
    for section, content in results.items():
        pdf.set_font("DejaVu", 'B', 14)
        pdf.cell(0, 10, section.upper(), ln=True)
        pdf.set_font("DejaVu", size=12)
        pdf.multi_cell(0, 10, content)
        pdf.ln(5)
    
    pdf_bytes = pdf.output(dest='S').encode('latin-1', errors='replace')
    return pdf_bytes

def evaluate_pitch_deck(pitch_deck_text, analyze_design=False):
    results = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_analyses = 6
    if analyze_design:
        total_analyses += 1
    progress_step = 100 / total_analyses
    current_progress = 0

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

    if analyze_design:
        status_text.text("Analyzing design elements...")
        design_prompt = DESIGN_ANALYSIS_PROMPT.format(pitch_deck_text=pitch_deck_text)
        design_analysis = call_claude_api(design_prompt)
        if design_analysis:
            results["design"] = design_analysis
            current_progress += progress_step
            progress_bar.progress(int(current_progress))

    status_text.text("Generating overall feedback...")
    feedback_prompt = OVERALL_FEEDBACK_PROMPT.format(pitch_deck_text=pitch_deck_text)
    overall_feedback = call_claude_api(feedback_prompt)
    if overall_feedback:
        results["overall_feedback"] = overall_feedback
        current_progress += progress_step
        progress_bar.progress(100)
        status_text.text("Analysis complete!")
    else:
        st.error("Failed to generate overall feedback.")
        return None

    return results

def display_evaluation_results(results):
    st.title("Pitch Deck Evaluation")
    tab_definitions = [
        {"label": "📖 Story Analysis", "key": "story"},
        {"label": "🚀 Startup Stage", "key": "startup_stage"},
        {"label": "🎯 Market Entry", "key": "market_entry"},
        {"label": "💼 Business Model", "key": "business_model"},
        {"label": "👥 Expert Panel", "key": "expert_panel"},
        {"label": "🎨 Design Analysis", "key": "design"},
        {"label": "📝 Overall Feedback", "key": "overall_feedback"}
    ]
    available_tabs = [tab for tab in tab_definitions if tab["key"] in results]
    tab_labels = [tab["label"] for tab in available_tabs]
    tabs = st.tabs(tab_labels)
    for i, tab in enumerate(available_tabs):
        with tabs[i]:
            content = results[tab["key"]]
            st.markdown(content)
            if tab["key"] == "market_entry" and "```dot" in content:
                dot_code = content.split("```dot")[1].split("```")[0].strip()
                st.graphviz_chart(dot_code)

def main():
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
            
            Contact us at Support@ProtoBots.ai
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
    
    main_container = st.container()
    with main_container:
        if "evaluation_results" not in st.session_state:
            st.markdown("<hr style='border: none; height: 2px; background: #ccc; box-shadow: 0 2px 2px -2px grey;'>", unsafe_allow_html=True)
            st.title("PitchMe")
            st.markdown("Get expert AI-powered feedback on your pitch deck to impress investors and secure funding.")
            st.markdown("<hr style='border: none; height: 2px; background: #ccc; box-shadow: 0 2px 2px -2px grey;'>", unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 1])
            with col1:
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
                            analysis_status = st.empty()
                            with analysis_status.container():
                                with st.spinner("Analyzing your pitch deck..."):
                                    results = evaluate_pitch_deck(pitch_deck_text, analyze_design)
                                    if results:
                                        st.session_state.evaluation_results = results
                                        st.success("Analysis complete! Displaying results...")
                                        time.sleep(1)
                                        main_container.empty()
                                        display_evaluation_results(results)
                                        pdf_bytes = export_results_to_pdf(st.session_state.evaluation_results)
                                        st.download_button(
                                            label="Export Analysis as PDF",
                                            data=pdf_bytes,
                                            file_name="PitchMe_Analysis.pdf",
                                            mime="application/pdf"
                                        )
                                        if st.button("Evaluate Another Pitch Deck", type="primary"):
                                            for key in list(st.session_state.keys()):
                                                del st.session_state[key]
                                            st.experimental_rerun()
            with col2:
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
                st.header("Supported Formats")
                st.markdown("""
                We support multiple presentation formats:
                
                - **PDF** (.pdf)
                - **PowerPoint** (.ppt, .pptx)
                - **Word Documents** (.doc, .docx)
                """)
        else:
            display_evaluation_results(st.session_state.evaluation_results)
            if st.button("Evaluate Another Pitch Deck", type="primary"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.experimental_rerun()

if __name__ == "__main__":
    main()
