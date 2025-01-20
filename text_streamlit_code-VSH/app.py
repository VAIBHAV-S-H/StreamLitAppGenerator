import streamlit as st
from langchain_groq import ChatGroq
import re
import subprocess
import sys
import os
# Configure page layout
st.set_page_config(layout="wide")
# Initialize session state
if "generated_code_executed" not in st.session_state:
    st.session_state.generated_code_executed = False
if "cleaned_code" not in st.session_state:
    st.session_state.cleaned_code = ""
if "generated_code" not in st.session_state:
    st.session_state.generated_code = ""
if "temp_file_path" not in st.session_state:
    st.session_state.temp_file_path = "temp_app.py"
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "llama-3.1-70b-versatile"  # Default model
def select_model(prompt):
    """Dynamically select a valid model based on user prompt."""
    model_map = {
        "graph": "llama-3.1-13b",
        "calculator": "llama-3.1-70b-versatile",
        "data analysis": "llama-3.1-13b",
        "text generation": "llama-3.1-7b",
        "language translation": "llama-3.1-20b-multilingual",
        "code generation": "llama-3.1-20b-code",
        "QA": "llama-3.1-20b-qa",
    }
    free_model_map = {
        "llama-3.1-70b-versatile": True,
        "llama-3.1-13b": True,
        "llama-3.1-20b-versatile": True,
    }
    default_model = "llama-3.1-70b-versatile"
    # Check for available models in the prompt and default to free models
    for keyword, model in model_map.items():
        if keyword in prompt.lower():
            if model in free_model_map:  # Check if the model is free
                st.session_state.selected_model = model
                return model
    # Default to free models if no keyword match
    st.session_state.selected_model = default_model
    return default_model
def setup_groq():
    """Initialize the Groq API client with a dynamically selected model."""
    groq_api_key = st.sidebar.text_input("Enter your Groq API key:", type="password")
    if groq_api_key:
        try:
            return ChatGroq(
                temperature=0.7,
                groq_api_key=groq_api_key,
                model=st.session_state.selected_model,
            )
        except Exception as e:
            st.error(f"Error initializing Groq: {e}")
            return None
    else:
        st.warning("Please enter your Groq API key to proceed.")
    return None
def clean_code(code):
    """Clean the generated code by removing unnecessary markdown formatting."""
    code = re.sub(r"```python\n", "", code)  # Remove starting markdown code block
    code = re.sub(r"\n```", "", code)  # Remove ending markdown code block
    return code.strip()
def generate_streamlit_code(prompt, groq_llm):
    """Generate Streamlit application code based on user prompt."""
    try:
        selected_model = select_model(prompt)
        st.write(f"Using model: {selected_model} for generation.")
        system_prompt = """You are a specialized Streamlit application generator. Generate only the Python code without any markdown formatting or explanations. The code should:
1. Not use st.set_page_config
2. Include appropriate widgets and display elements
3. Handle user interactions and maintain state
4. Be complete and functional with all required imports"""
        user_prompt = f"Generate a Streamlit application that {prompt}"
        response = groq_llm.invoke(f"{system_prompt}\n\n{user_prompt}")
        if not response or not hasattr(response, "content"):
            raise ValueError("Invalid response from Groq API.")
        return response.content.strip('"""')  # Remove triple quotes from start and end
    except Exception as e:
        return f"Error generating code: {str(e)}"
def extract_modules(code):
    """Extract required modules from import statements in the code."""
    modules = set()
    import_pattern = (
        r"^(?:import\s+([a-zA-Z0-9_\.]+)|from\s+([a-zA-Z0-9_\.]+)\s+import)"
    )
    for line in code.splitlines():
        match = re.match(import_pattern, line.strip())
        if match:
            module_name = match.group(1) or match.group(2)
            modules.add(module_name.split(".")[0])
    return modules
def check_and_install_libraries(libraries):
    """Ensure all required libraries are installed."""
    logs = []
    for library in libraries:
        try:
            __import__(library)
        except ImportError:
            logs.append(f"Installing {library}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", library])
                logs.append(f"Successfully installed {library}.")
            except subprocess.CalledProcessError as e:
                logs.append(f"Failed to install {library}: {str(e)}")
                st.error(f"Failed to install {library}: {str(e)}")
    return logs
def execute_code(code):
    temp_file_path = st.session_state.temp_file_path  # Use session state variable here
    with open(temp_file_path, "w") as f:
        f.write(code)
    # Run the Streamlit app in a new browser window
    subprocess.Popen(["streamlit", "run", temp_file_path])
def main():
    groq_llm = setup_groq()
    st.header("Streamlit Code Generator")
    prompt = st.text_area(
        "Enter your prompt:",
        height=100,
        placeholder="Example: create a simple calculator app",
    )
    if st.button("Generate Code"):
        if not groq_llm:
            st.error("Please enter your Groq API key in the sidebar first!")
            return
        with st.spinner("Generating code..."):
            generated_code = generate_streamlit_code(prompt, groq_llm)
            st.session_state.generated_code = generated_code
            st.session_state.cleaned_code = clean_code(generated_code)
            st.code(st.session_state.cleaned_code, language="python")
    if st.button("Run Generated Code") and st.session_state.cleaned_code:
        extracted_modules = extract_modules(st.session_state.cleaned_code)
        required_libraries = ["streamlit"] + list(extracted_modules)
        with st.spinner("Installing required libraries..."):
            logs = check_and_install_libraries(required_libraries)
            for log in logs:
                st.write(log)
        execute_code(st.session_state.cleaned_code)
    if st.button("Delete Temporary File"):
        try:
            if os.path.exists(st.session_state.temp_file_path):
                os.remove(st.session_state.temp_file_path)
                st.success("Temporary file deleted.")
            else:
                st.warning("No temporary file found.")
        except PermissionError:
            st.error("Permission denied: Unable to delete the file.")
        except Exception as e:
            st.error(f"Error deleting file: {str(e)}")
if __name__ == "__main__":
    main()
