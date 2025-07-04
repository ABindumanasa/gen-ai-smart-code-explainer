import streamlit as st
import requests
import time
from typing import Dict, Any

# Page config
st.set_page_config(
    page_title="AI Code Explainer",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styles
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .code-container {
        background-color: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        white-space: pre-wrap;
    }
    .explanation-container {
        background-color: #e8f5e8;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        white-space: pre-wrap;
    }
    .stButton > button {
        background-color: #667eea;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #5a67d8;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header"><h1>🤖 AI Code Explainer</h1><p>Understand any code snippet in plain English!</p></div>', unsafe_allow_html=True)

# Sidebar config
st.sidebar.header("⚙️ Configuration")

# Load credentials from Streamlit secrets or fallback to manual input
api_key = st.secrets.get("ibm", {}).get("api_key", "")
project_id = st.secrets.get("ibm", {}).get("project_id", "")

if api_key and project_id:
    st.sidebar.success("✅ Credentials loaded from secrets")
    # Hide sensitive information - only show that credentials are loaded
else:
    st.sidebar.warning("⚠️ Secrets not found, please enter manually")
    api_key = st.sidebar.text_input("IBM API Key", type="password", help="Enter your IBM Cloud API key")
    project_id = st.sidebar.text_input("Project ID", help="Enter your watsonx.ai project ID")

region = st.sidebar.selectbox("Region", ["us-south", "eu-de", "eu-gb", "jp-tok"])

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
    st.header("📝 Code Input")
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
    st.header("🤖 AI Explanation")
    
    if st.button("🔍 Explain Code", disabled=not code_input or not api_key or not project_id):
        if code_input.strip():
            with st.spinner("🤖 AI is analyzing your code..."):
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
            st.warning("⚠️ Please enter some code to explain!")
    
    # Display current explanation
    if st.session_state.explanation_history:
        latest = st.session_state.explanation_history[-1]
        st.markdown('<div class="explanation-container">', unsafe_allow_html=True)
        st.markdown("**🤖 AI Explanation:**")
        st.write(latest['explanation'])
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Download explanation
        if st.button("📥 Download Explanation"):
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
    st.header("📚 Explanation History")
    
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
    if st.button("🗑️ Clear History"):
        st.session_state.explanation_history = []
        st.rerun()

# Footer
st.markdown("---")
st.markdown("🤖 **AI Code Explainer** | Powered by IBM watsonx.ai | Built with Streamlit")

# Tips section
with st.expander("💡 Tips for Better Explanations"):
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
with st.expander("ℹ️ About"):
    st.markdown("""
    This AI Code Explainer uses IBM watsonx.ai to provide intelligent code explanations.
    Simply paste your code, select your preferences, and get clear explanations in plain English.
    
    **Features:**
    - Multiple programming languages supported
    - Adjustable explanation detail levels
    - Various AI models to choose from
    - Explanation history and download functionality
    - Beautiful, responsive interface
    
    **Setup:**
    1. Get your IBM Cloud API key and watsonx.ai project ID
    2. Either add them to Streamlit secrets or enter them in the sidebar
    3. Start explaining code!
    """)
