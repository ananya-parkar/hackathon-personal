import streamlit as st
from PyPDF2 import PdfReader
import os
from backend.upload import save_uploaded_files
from backend.process import chunk_text_with_sources, create_faiss_index
from backend.retrieval import search_similar_chunks
from backend.ollama_handler import query_ollama
from backend.ner_utils import extract_entities
from backend.utils import extract_text_from_file
from backend.lang_utils import detect_language
from backend.logger import log_interaction
# ====== PAGE CONFIG ======
st.set_page_config(
    page_title="📄 Doc Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====== CUSTOM CSS ======
st.markdown("""
<style>
    body {
        background-color: #f8f9fa;
        margin: 0;
        padding: 0;
    }

    .main {
        background-color: #f8f9fa;
        color: #1a2a3a;
        font-family: 'Segoe UI', sans-serif;
    }
    h1 {
        color: #336699;
        text-align: center;
        font-size: 42px;
        margin-bottom: 0.5em;
    }
    h2, h3 {
        color: #4b6270;
        margin-top: 1em;
    }
    .stButton>button {
        background-color: #336699;
        color: white;
        border-radius: 6px;
        padding: 0.6em 1.2em;
        font-weight: bold;
        margin: 0.5em 0;
    }
    .stTextInput>div>div>input {
        border: 2px solid #aad4ff;
        border-radius: 8px;
        padding: 10px;
        font-size: 16px;
    }
    .stFileUploader {
        border: 2px dashed #99ccff;
        border-radius: 12px;
        padding: 30px;
        background-color: #e6f2ff;
        text-align: center;
    }
    .stTextArea textarea {
        background-color: #f9fcff;
        border-radius: 8px;
        border: 1px solid #aad4ff;
    }
    .stMarkdown {
        font-size: 16px;
        line-height: 1.6;
    }
    .sidebar .sidebar-content {
        background-color: #f0f9ff;
        padding: 1.5em;
        border-radius: 0 12px 12px 0;
    }
    .stSuccess {
        border-radius: 8px;
        padding: 1em;
        background-color: #e1f7e6;
        color: #2e7d32;
    }
    .stExpander {
        border: 1px solid #aad4ff;
        border-radius: 8px;
        background-color: #f9fcff;
    }
    .file-summary {
        background-color: #e6f2ff;
        border-radius: 8px;
        padding: 1em;
        margin: 1em 0;
    }
    .entity-list {
        font-family: monospace;
        background-color: #f9fcff;
        border-radius: 8px;
        padding: 1em;
        margin: 0.5em 0;
    }
</style>
""", unsafe_allow_html=True)

# ====== SIDEBAR ======
with st.sidebar:
    st.markdown("## 🛠️ Navigation")
    st.markdown("""
    - **📂 Upload PDFs**
    - **🧠 Ask Questions**
    - **🔍 View Entities**
    """)
    st.markdown("---")
    st.markdown("**About**")
    st.markdown("""
    This app uses NLP and AI to analyze your documents and answer your questions.
    """)

# ====== MAIN CONTENT ======
st.markdown("# 🧠 Multi-Document Analyzer")
st.markdown("Upload your PDFs and ask anything. The app uses NER + semantic search + Ollama to give intelligent answers.")

# ====== UPLOAD SECTION ======
st.markdown("## 📂 Upload Files")
uploaded_files = st.file_uploader(
    "Drag and drop your PDFs here",
    type=["pdf", "docx", "txt", "md", "html", "xls", "xlsx", "pptx", "jpg", "jpeg", "png", "tiff", "zip"],
    accept_multiple_files=True
)

# ====== GLOBAL SESSION STATE ======
if "file_text_map" not in st.session_state:
    st.session_state.file_text_map = {}
if "ner_summary" not in st.session_state:
    st.session_state.ner_summary = {}

# ====== AUTO-PROCESS FILES ======
if uploaded_files:
    with st.spinner("🔍 Processing uploaded files..."):
        st.session_state.file_text_map.clear()
        st.session_state.ner_summary.clear()
        file_paths = save_uploaded_files(uploaded_files)
        for path in file_paths:
            try:
                text = extract_text_from_file(path)
                print("Extracted text for", os.path.basename(path), ":", text)
                st.session_state.file_text_map[os.path.basename(path)] = text
            except Exception as e:
                print(f"Skipping {path}: {e}")
        # Run NER
        for filename, text in st.session_state.file_text_map.items():
            entities = extract_entities(text)
            st.session_state.ner_summary[filename] = entities
        # Chunk + FAISS Index
        chunks = chunk_text_with_sources(st.session_state.file_text_map)
        print("Chunks generated from all files:")  # <--- ADD THIS LINE
        for chunk in chunks:
            print(chunk)
        create_faiss_index(chunks)
    st.success("✅ All documents indexed and entities extracted!")

# ====== FILE SUMMARY ======
if st.session_state.file_text_map:
    st.markdown("## 📝 File Summary")
    for filename in st.session_state.file_text_map:
        with st.container():
            st.markdown(f"**{filename}**")
            st.markdown(f"*{len(st.session_state.file_text_map[filename])} characters*")
            st.markdown("---")

# ====== QUESTION INPUT ======
st.markdown("## 💬 Ask a Question")
user_question = st.text_input(
    "Type your question below:",
    placeholder="What would you like to know?"
)

if user_question:
    with st.spinner("🤔 Thinking..."):
        matched_chunks = search_similar_chunks(user_question)
        print("Chunks matched for question:", user_question)
        for c in matched_chunks:
            print(c)
        context_str = "\n\n".join([f"[{c['source']}]\n{c['text']}" for c in matched_chunks])
        # Combine entities
        flat_entities = [f"{label}: {text}" for ents in st.session_state.ner_summary.values() for text, label in ents]
        entity_context = "\n".join(flat_entities) if flat_entities else "None"
        # Prompt
        with st.spinner("🤔 Thinking..."):
            matched_chunks = search_similar_chunks(user_question)
            context_str = "\n\n".join([f"[{c['source']}]\n{c['text']}" for c in matched_chunks])
            flat_entities = [f"{label}: {text}" for ents in st.session_state.ner_summary.values() for text, label in ents]
            entity_context = "\n".join(flat_entities) if flat_entities else "None"
            detected_lang = detect_language(user_question)
            prompt = f"""
            Use the extracted entities and document context below to answer the question.
            Don't make up information. If the answer is not found, say:
            "The answer is not available in the provided documents."

            Named Entities:
            {entity_context}

            Context:
            {context_str}

            Question ({detected_lang}): {user_question}
            Answer ({detected_lang}):
            Please answer in the same language as the question.
            """

    response = query_ollama(prompt)
     # ADD LOGGING HERE
    sources = list(set([chunk['source'] for chunk in matched_chunks]))
    log_interaction(user_question, response, sources)

    # ====== SHOW ANSWER ======
    st.markdown("### ✅ Response")
    st.markdown(response)
    # ====== SHOW ENTITIES ======
    with st.expander("🧠 View Detected Entities"):
        st.code(entity_context, language="text")
