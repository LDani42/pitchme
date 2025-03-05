import streamlit as st
import os
import tempfile
import anthropic
from PyPDF2 import PdfReader
from pathlib import Path
import time
import base64
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

# Task
Analyze the following pitch deck and identify the story it tells. Focus on the customer's problem, the solution, and their journey.

If there is no clear story, explain this and suggest a customer story for the pitch.

# Output Format
Provide your response in two sections with clear markdown headers (## for main sections, ### for subsections):

## 📝 Story Analysis
A brief summary of the story told in the pitch (or lack thereof). Use bullet points for clarity.

## 🔍 Storytelling Recommendations
Creative recommendations for improving the storytelling based on three approaches. Format each approach as a subsection (###) with clear recommendations:

### The Hero's Journey
- **Strengths**: "This is good because..." 
- **Improvements**: "I suggest you can improve this by..."

### The Customer's Tale
- **Strengths**: "This is good because..." 
- **Improvements**: "I suggest you can improve this by..."

### The Industry's Point of View
- **Strengths**: "This is good because..." 
- **Improvements**: "I suggest you can improve this by..."

Use bold text for important points, create tables for comparing approaches, and utilize emojis to make the content more visually engaging.

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
Provide your response using clear markdown formatting:

## 🚀 Current Stage
Create a visual indicator showing where the startup is on the journey, like:
Ideation → [MVC] → IPR → MVP → MVR

Explain which stage the startup is at and justify with specific evidence from the pitch deck. Use bullet points to list the evidence.

## 📋 Stage Definition
Provide the definition of the identified stage with clear formatting.

## 🔮 Next Stage Planning
Create a visual roadmap showing how to get to the next stage. Use a table format with these columns:
| Current Status | Next Milestone | Action Items |
Include 3-5 key actions the startup should take to reach the next stage.

Use bold text for important points and emojis to make the content visually engaging.

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
Provide your response using clear markdown formatting with visual elements:

## 🎯 Customer Segment Analysis
Create a target diagram using mermaid syntax to represent how well they've identified their critical customer segment.

Evaluate how well they've identified their critical customer segment, using bullet points for clarity and bold text for key insights.

## 🌊 Strategy Classification
Generate a mermaid diagram that visually represents the position on the Blue Ocean vs Red Ocean spectrum. The diagram should be a horizontal flow with nodes indicating "Red Ocean" and "Blue Ocean" and an indicator node positioned accordingly.

Determine if they're using Blue Ocean or Red Ocean strategy with evidence. Use a comparison table:

| Blue Ocean Indicators | Red Ocean Indicators |
| --------------------- | -------------------- |
| (List evidence) | (List evidence) |

## 📈 Market Entry Recommendations
Provide recommendations to sharpen their customer segment focus and strengthen their chosen strategy. Format as:

### Strengths:
- "This is good because..." (bullet points)

### Improvements:
- "I suggest you can improve this by..." (bullet points)

Use emojis, bold text, and clear formatting to make the content visually engaging.

# Pitch Deck Content
{pitch_deck_text}
"""

BUSINESS_MODEL_PROMPT = """
# Role
You are a Business Model Expert specializing in startup evaluation.

# Task
Evaluate the following pitch deck using the Business Model Canvas framework. Score each element from 0-10 (0 = not addressed, 10 = excellent).

# Output Format
Create a visually appealing report with clear markdown formatting:

## 💼 Business Model Canvas Evaluation

For each Business Model Canvas element, create a subsection with the following format:

### [Element Name] 📊 Score: [X/10]

#### Evidence:
> Quote relevant text from the pitch deck (in blockquote format)

#### Strengths:
- ✅ "This is good because..." (bullet points)

#### Areas for Improvement:
- 🔄 "I suggest you can improve this by..." (bullet points)
OR
- ❓ "Not addressed. Go out and talk to experts! Try contacting... and ask them..."
OR
- 🔍 "Not addressed. How does your competitor's business or financial model address..."

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

End with a visual summary table showing scores for all elements:

| Element | Score | Key Insight |
| ------- | ----- | ----------- |
| [Element] | [Score] | [Brief comment] |

Also create a radar chart representation using mermaid syntax to visualize the scores across all elements.

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
Create a visually engaging panel discussion report with clear markdown formatting:

## 👥 Expert Panel Feedback

For each expert, create a profile and feedback section:

### 👨‍💼 [Expert Title]
**Focus Areas**: [key evaluation criteria]

#### Key Observations:
> Quote relevant text from the pitch deck (in blockquote format)

#### Feedback:
- ✅ **Strengths**: "This is good because..." (bullet points)
- 🔄 **Suggestions**: "I suggest you can improve this by..." (bullet points)
- ❓ **Questions**: "The expert would ask..." (if applicable)

End with a panel summary showing the overall consensus, areas of agreement, and any conflicting viewpoints. Create a table showing each expert's key recommendation:

| Expert | Key Recommendation | Priority Level |
| ------ | ------------------ | -------------- |
| [Expert] | [Recommendation] | [High/Medium/Low] |

Use emojis, bold text, and clear formatting to make the content visually engaging.

# Pitch Deck Content
{pitch_deck_text}
"""

OVERALL_FEEDBACK_PROMPT = """
# Role
You are a Startup Mentor with expertise in pitch deck evaluation and fostering a learning mindset.

# Task
Provide comprehensive feedback on the following pitch deck.

# Output Format
Create a visually engaging executive summary with clear markdown formatting:

## 📝 Executive Summary

### ✨ Strengths
Create a visual scorecard for 3-5 key strengths of the pitch deck. For each strength:
- **[Strength Title]**: Detailed explanation with specific examples from the pitch deck
- **Impact**: Why this matters for investors and customers
- **Leverage Point**: How to maximize this strength

### 🔍 Areas for Improvement
Create a prioritized list of 3-5 specific areas where the pitch could be enhanced:
- **[Area Title]** (Priority: High/Medium/Low)
  - **Current State**: What the pitch currently shows
  - **Desired State**: What would make it more compelling
  - **Gap Analysis**: What's missing and why it matters

### 🚀 Action Plan
Create a table with 3-5 concrete actions:

| Action Item | Expected Impact | Difficulty | Timeline |
| ----------- | --------------- | ---------- | -------- |
| [Action] | [Impact] | [Easy/Medium/Hard] | [Timeframe] |

### 💭 Motivational Closing
A paragraph that encourages the team to view feedback as an opportunity for growth, emphasizing the learning mindset. Use metaphors and inspirational language that connects to the startup's mission.

Use emojis, bold text, tables, and clear formatting to make the content visually engaging.

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
Create a visually engaging design analysis with clear markdown formatting:

## 🎨 Design Elements Analysis
Create a visual checklist of design elements likely present in the pitch deck:

- [ ] Professional color scheme
- [ ] Consistent typography
- [ ] High-quality images
- [ ] Effective charts/graphs
- [ ] Clear slide layouts
- [ ] Visual hierarchy
- [ ] Branded elements

For each element detected, change [ ] to [x] and provide evidence from the content.

## 🔍 Visual Branding Evaluation
Create a mock brand guideline based on the inferred elements:
- **Colors**: Likely palette (based on any color mentions)
- **Typography**: Inferred font choices and hierarchy
- **Imagery**: Types of visuals mentioned
- **Layout**: Structure and organization patterns

## 💡 Design Recommendations
Organize recommendations by category:

### Slide Layouts
- ✅ **Strengths**: "This appears well-designed because..." (based on the content)
- 🔄 **Improvements**: "Consider improving this by..."

### Color Scheme
- ✅ **Strengths**: "This appears well-designed because..."
- 🔄 **Improvements**: "Consider improving this by..."

(Repeat for Typography, Charts/Diagrams, Image Selection, Visual Storytelling)

End with a visual "before/after" concept using mermaid syntax to illustrate key improvements.

Use emojis, bold text, and clear formatting to make the content visually engaging.

# Pitch Deck Content
{pitch_deck_text}
"""

# Add CSS for styling, with dark mode support
def add_custom_css():
    st.markdown("""
    <style>
        /* Basic styling */
        h1, h2, h3 { margin-bottom: 1rem; }
        p, li, div { line-height: 1.6; }
        
        /* Sidebar styling */
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
            border-radius: 4px 4px 0px 0px;
            padding: 10px 16px;
            font-weight: 500;
            border: 1px solid #e2e8f0;
            border-bottom: none;
            margin-right: 4px;
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
            border-left: 5px solid #2a70ba;
            padding: 10px 15px;
            margin: 10px 0;
        }
        
        /* Table styling */
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
        }
        
        /* Responsive design adjustments */
        @media (max-width: 768px) {
            .row-widget.stButton {
                width: 100%;
            }
            
            /* Make tables scrollable on mobile */
            .stTable {
                overflow-x: auto;
                display: block;
            }
            
            /* Better spacing for mobile */
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
        }
        
        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
            .stApp {
                background-color: #0e1117;
            }
            
            p, li, span, div {
                color: #f9fafb !important;
            }
            
            h1, h2, h3, h4, h5, h6 {
                color: #e5e7eb !important;
            }
            
            .stTabs [data-baseweb="tab"] {
                background-color: #1e2530;
                color: #e5e7eb;
                border-color: #4b5563;
            }
            
            table {
                border-color: #4b5563;
            }
            
            th, td {
                border-color: #4b5563;
                color: #e5e7eb;
            }
            
            blockquote {
                background-color: #1e2530;
                color: #e5e7eb;
            }
        }
        
        /* Upload section styling */
        .upload-section {
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        /* Features section styling */
        .features-section {
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        /* Supported formats section styling */
        .formats-section {
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        /* Dark mode styling for sections */
        @media (prefers-color-scheme: dark) {
            .upload-section, .features-section, .formats-section {
                background-color: #1e2530;
            }
        }
        
        /* Light mode styling for sections */
        @media (prefers-color-scheme: light) {
            .upload-section, .features-section, .formats-section {
                background-color: white;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }
        }
        
        /* Emoji sizing */
        em {
            font-style: normal;
        }
    </style>
    """, unsafe_allow_html=True)

add_custom_css()

# Function to encode company logo for display
def get_company_logo():
    try:
        # Use the file path relative to the app.py file
        return st.image("ProtoBots_Logo_Circle.png", width=80)
    except Exception as e:
        st.error(f"Error loading logo: {str(e)}")
        # Fallback to text if image fails to load
        return st.markdown("<h3>ProtoBots.ai</h3>", unsafe_allow_html=True)
