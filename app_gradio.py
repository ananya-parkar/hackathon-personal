import gradio as gr
from PyPDF2 import PdfReader
import os
from backend.upload import save_uploaded_files
from backend.process_grad import chunk_text_with_sources, create_faiss_index
from backend.retrieval import search_similar_chunks
from backend.ollama_handler import query_ollama
from backend.ner_utils import extract_entities
# Global state
file_text_map = {}
ner_summary = {}
# Function to process documents
def process_documents(files):
   global file_text_map, ner_summary
   try:
       file_text_map.clear()
       ner_summary.clear()
       file_paths = save_uploaded_files(files)
       for path in file_paths:
           reader = PdfReader(path)
           text = "".join([page.extract_text() or "" for page in reader.pages])
           file_text_map[os.path.basename(path)] = text
       for filename, text in file_text_map.items():
           entities = extract_entities(text)
           ner_summary[filename] = entities
       chunks = chunk_text_with_sources(file_text_map)
       create_faiss_index(chunks)
       return "✅ Documents processed successfully!"
   except Exception as e:
       return f"❌ Error: {str(e)}"
# Function to answer questions
def answer_question(typed_question):
   matched_chunks = search_similar_chunks(typed_question)
   context_str = "\n\n".join([f"[{c['source']}]\n{c['text']}" for c in matched_chunks])
   flat_entities = [f"{label}: {text}" for ents in ner_summary.values() for text, label in ents]
   entity_context = "\n".join(flat_entities) if flat_entities else "None"
   prompt = f"""
Use the extracted entities and document context below to answer the question.
Don't make up information. If the answer is not found, say:
"The answer is not available in the provided documents."
Named Entities:
{entity_context}
Context:
{context_str}
Question: {typed_question}
Answer:
"""
   response = query_ollama(prompt)
   return typed_question, response
# ===================== 💅 Stylish Gradio UI =====================
with gr.Blocks(theme=gr.themes.Soft()) as demo:
   gr.HTML("<h1 style='text-align:center; color:#336699;'>📄 Multi-Document Analyzer</h1>")
   with gr.Tab("📁 Upload & Process"):
       gr.Markdown("### Upload one or more PDF documents")
       file_input = gr.File(label="Choose PDF files", file_types=[".pdf"], file_count="multiple")
       process_button = gr.Button("🔍 Process Documents", elem_id="process-btn")
       status_output = gr.Textbox(label="Status", interactive=False, lines=2)
       process_button.click(fn=process_documents, inputs=file_input, outputs=status_output)
   with gr.Tab("💬 Ask a Question"):
       gr.Markdown("### Ask anything based on the uploaded documents")
       typed_question = gr.Textbox(label="Type your question here...", placeholder="e.g. What is the project deadline?")
       ask_button = gr.Button("🤖 Ask the AI")
       final_question = gr.Textbox(label="📥 Final Question", interactive=False)
       response_output = gr.Textbox(label="📤 AI's Answer", lines=6)
       ask_button.click(
           fn=answer_question,
           inputs=typed_question,
           outputs=[final_question, response_output]
       )
   gr.Markdown("<hr style='margin-top:30px;'>")
   gr.HTML("<p style='text-align:center; color:gray;'>Created by Anshika 💙</p>")
demo.launch(inbrowser=True)