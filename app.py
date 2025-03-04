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

# Add CSS for styling
def add_custom_css():
    st.markdown("""
    <style>
        /* Basic text colors */
        h1, h2, h3 { color: #1a365d; }
        p, li, div { color: #333333; }
        
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
        
        /* Custom card styling */
        .custom-card {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
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

# Function to call Claude API
def call_claude_api(client, prompt, max_tokens=4000):
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

# Simple demo prompt
DEMO_PROMPT = """
Analyze this pitch deck content and give feedback on the overall presentation quality.

Content:
{pitch_deck_text}
"""

def main():
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/data-quality.png", width=80)
        st.title("PitchMe")
        st.markdown("Upload your pitch deck to get expert evaluation.")
        
        with st.expander("ℹ️ About"):
            st.markdown("""
            This app evaluates your pitch deck with AI-powered feedback to help improve your presentation.
            """)
        
        st.divider()
        st.markdown("Made by ProtoBots.ai")
    
    # Main content
    st.title("Pitch Deck Evaluator")
    st.markdown("Upload your pitch deck to get expert feedback.")
    
    uploaded_file = st.file_uploader("Upload your pitch deck (PDF)", type="pdf")
    
    if uploaded_file is not None:
        st.write(f"File uploaded: {uploaded_file.name}")
        
        if st.button("Evaluate Pitch Deck", type="primary"):
            client = get_anthropic_client()
            
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Extract text
            status_text.text("Extracting text from PDF...")
            pitch_deck_text = extract_text_from_pdf(uploaded_file)
            progress_bar.progress(25)
            
            if not pitch_deck_text or len(pitch_deck_text) < 100:
                st.error("Could not extract sufficient text from the PDF.")
            else:
                # Generate analysis
                status_text.text("Analyzing pitch deck...")
                demo_prompt = DEMO_PROMPT.format(pitch_deck_text=pitch_deck_text)
                analysis = call_claude_api(client, demo_prompt)
                progress_bar.progress(100)
                
                if analysis:
                    status_text.text("Analysis complete!")
                    st.markdown("## Analysis Results")
                    st.markdown(analysis)
                else:
                    st.error("Failed to generate analysis. Please try again.")

if __name__ == "__main__":
    main()
