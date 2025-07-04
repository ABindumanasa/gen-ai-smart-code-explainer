import streamlit as st
import requests
import time
from typing import Dict, Any

# Page config
st.set_page_config(
    page_title="Smart Code Analyzer",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styles
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #2c3e50 0%, #34495e 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .author-name {
        text-align: center;
        color: #7f8c8d;
        font-size: 1.1rem;
        margin-top: 0.5rem;
        font-style: italic;
    }
    .code-container {
        background-color: #ffffff;
        border-left: 4px solid #2c3e50;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        white-space: pre-wrap;
        border: 1px solid #e0e0e0;
        color: #2c3e50;
    }
    .explanation-container {
        background-color: #f8fff8;
        border-left: 4px solid #27ae60;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        white-space: pre-wrap;
        border: 1px solid #d4e6d4;
        color: #2c3e50;
    }
    .stButton > button {
        background-color: #2c3e50;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #34495e;
        transform: translateY(-2px);
    }
    .stSelectbox > div > div {
        background-color: #ffffff;
        border: 1px solid #bdc3c7;
        color: #2c3e50;
    }
    .stTextArea > div > div > textarea {
        background-color: #ffffff;
        border: 1px solid #bdc3c7;
        color: #2c3e50;
    }
    .sidebar-header {
        background: linear-gradient(90deg, #27ae60 0%, #2ecc71 100%);
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .stSidebar {
        background-color: #fafafa;
    }
    .stSidebar .stSelectbox label {
        color: #2c3e50;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header"><h1>Smart Code Analyzer</h1><p>Understand any code snippet in plain English!</p></div>', unsafe_allow_html=True)
st.markdown('<div class="author-name">by Bindu Manasa</div>', unsafe_allow_html=True)

# Sidebar config
st.sidebar.markdown('<div class="sidebar-header"><h3>Configuration</h3></div>', unsafe_allow_html=True)

# Load credentials from Streamlit secrets (hidden from user interface)
api_key = st.secrets.get("ibm", {}).get("api_key", "")
project_id = st.secrets.get("ibm", {}).get("project_id", "")
region = st.secrets.get("ibm", {}).get("region", "us-south")

# Only show model selection and preferences
model_choice = st.sidebar.selectbox(
    "Select Model",
    [
        "meta-llama/llama-3-2-3b-instruct",
        "google/flan-ul2",
        "mistralai/mixtral-8x7b-instruct-v01"
    ]
)

programming_language = st.sidebar.selectbox(
    "Programming Language",
    ["Python", "JavaScript", "Java", "C++", "C#", "Go", "Rust", "PHP", "Ruby", "Swift", "Other"]
)

detail_level = st.sidebar.select_slider(
    "Explanation Detail Level",
    options=["Beginner", "Intermediate", "Advanced"],
    value="Beginner"
)

# Initialize explanation history
if 'explanation_history' not in st.session_state:
    st.session_state.explanation_history = []

# Sample code snippets
sample_codes = {
    "Python - Fibonacci": '''def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))''',

    "JavaScript - Array Filter": '''const numbers = [1,2,3,4,5,6,7,8,9,10];
const evenNumbers = numbers.filter(num => num % 2 === 0);
console.log(evenNumbers);''',

    "Python - Class Example": '''class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def area(self):
        return self.width * self.height''',

    "Custom": "Enter your own code..."
}

# Layout: two columns
col1, col2 = st.columns([1,1])

with col1:
    st.header("Code Input")
    sample_choice = st.selectbox("Choose a sample or enter custom code:", list(sample_codes.keys()))

    if sample_choice == "Custom":
        code_input = st.text_area(
            "Enter your code here:",
            height=300,
            placeholder="Paste your code snippet here..."
        )
    else:
        code_input = st.text_area(
            "Code to explain:",
            value=sample_codes[sample_choice],
            height=300
        )

def get_explanation_prompt(code: str, language: str, detail_level: str) -> str:
    """Generate a prompt for code explanation based on detail level."""
    base_prompt = f"""Please explain this {language} code in plain English, suitable for a {detail_level.lower()} programmer.

Code:
```{language.lower()}
{code}
```

Please provide:
1. A brief overview of what the code does
2. Step-by-step explanation of each major part
3. Key concepts or patterns used
4. Any potential improvements or considerations

Make the explanation clear and easy to understand for someone at the {detail_level.lower()} level."""
    
    return base_prompt

def get_access_token(api_key: str) -> str:
    """Get IBM Cloud access token."""
    url = "https://iam.cloud.ibm.com/identity/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key
    }
    
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Failed to get access token: {response.text}")

def explain_code_with_watsonx(code: str, language: str, detail_level: str, 
                             api_key: str, project_id: str, region: str, model: str) -> str:
    """Explain code using IBM watsonx.ai."""
    try:
        # Get access token
        access_token = get_access_token(api_key)
        
        # Prepare the request
        url = f"https://{region}.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        prompt = get_explanation_prompt(code, language, detail_level)
        
        body = {
            "input": prompt,
            "parameters": {
                "decoding_method": "greedy",
                "max_new_tokens": 1000,
                "temperature": 0.3,
                "repetition_penalty": 1.1
            },
            "model_id": model,
            "project_id": project_id
        }
        
        # Make the request
        response = requests.post(url, headers=headers, json=body)
        
        if response.status_code == 200:
            result = response.json()
            return result['results'][0]['generated_text']
        else:
            return f"Error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Error explaining code: {str(e)}"

# Continue with column 2
with col2:
    st.header("AI Explanation")
    
    # Show status based on credentials
    if api_key and project_id:
        status_message = "Ready to analyze code"
        button_disabled = not code_input
    else:
        status_message = "Please configure API credentials in secrets"
        button_disabled = True
    
    st.info(status_message)
    
    if st.button("Analyze Code", disabled=button_disabled):
        if code_input.strip():
            with st.spinner("AI is analyzing your code..."):
                explanation = explain_code_with_watsonx(
                    code_input, 
                    programming_language, 
                    detail_level,
                    api_key, 
                    project_id, 
                    region, 
                    model_choice
                )
                
                # Store in history
                st.session_state.explanation_history.append({
                    'code': code_input,
                    'language': programming_language,
                    'detail_level': detail_level,
                    'explanation': explanation,
                    'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
                })
        else:
            st.warning("Please enter some code to explain!")
    
    # Display current explanation
    if st.session_state.explanation_history:
        latest = st.session_state.explanation_history[-1]
        st.markdown('<div class="explanation-container">', unsafe_allow_html=True)
        st.markdown("**AI Explanation:**")
        st.write(latest['explanation'])
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Download explanation
        if st.button("Download Explanation"):
            explanation_text = f"""Code Explanation
=================
Language: {latest['language']}
Detail Level: {latest['detail_level']}
Generated: {latest['timestamp']}

Code:
{latest['code']}

Explanation:
{latest['explanation']}
"""
            st.download_button(
                label="Download as .txt",
                data=explanation_text,
                file_name=f"code_explanation_{latest['timestamp'].replace(':', '-').replace(' ', '_')}.txt",
                mime="text/plain"
            )

# Explanation History Section
if st.session_state.explanation_history:
    st.header("Explanation History")
    
    for i, item in enumerate(reversed(st.session_state.explanation_history)):
        with st.expander(f"Explanation {len(st.session_state.explanation_history) - i} - {item['language']} ({item['timestamp']})"):
            col_code, col_exp = st.columns([1, 1])
            
            with col_code:
                st.markdown("**Code:**")
                st.markdown(f"<div class='code-container'><code>{item['code']}</code></div>", unsafe_allow_html=True)
            
            with col_exp:
                st.markdown(f"**Explanation ({item['detail_level']} level):**")
                st.markdown(f"<div class='explanation-container'>{item['explanation']}</div>", unsafe_allow_html=True)
    
    # Clear history button
    if st.button("Clear History"):
        st.session_state.explanation_history = []
        st.rerun()

# Footer
st.markdown("---")
st.markdown("**Smart Code Analyzer** | Powered by IBM watsonx.ai | Built with Streamlit")

# Tips section
with st.expander("Tips for Better Explanations"):
    st.markdown("""
    - **Be specific about the programming language** for more accurate explanations
    - **Choose the right detail level**: 
        - Beginner: Simple explanations with basic concepts
        - Intermediate: More technical details and best practices
        - Advanced: In-depth analysis and optimization suggestions
    - **Provide complete code snippets** when possible for better context
    - **Try different models** to see which gives you the best explanations
    """)

# About section
with st.expander("About"):
    st.markdown("""
    This Smart Code Analyzer uses IBM watsonx.ai to provide intelligent code explanations.
    Simply paste your code, select your preferences, and get clear explanations in plain English.
    
    **Features:**
    - Multiple programming languages supported
    - Adjustable explanation detail levels
    - Various AI models to choose from
    - Explanation history and download functionality
    - Clean, responsive interface
    
    **Setup:**
    Configure your IBM Cloud API key and watsonx.ai project ID in Streamlit secrets to get started.
    """)
