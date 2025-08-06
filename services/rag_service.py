# services/rag_service.py
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from typing import Optional, List

# --- Global variable to hold the RAG retriever ---
_rag_retriever = None

_rag_retriever = None

def setup_rag_from_file(file_path: str):
    """
    Sets up the RAG system by reading a text file, splitting it into chunks,
    creating embeddings, and building a searchable vector store.
    """
    global _rag_retriever
    if _rag_retriever is not None:
        print("RAG service already initialized.")
        return

    print("Setting up RAG service from file...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # --- FIX: Read the entire file and split by "Q:" to get individual Q&A blocks ---
            full_text = f.read()
            # We split by "Q:" and filter out any empty strings that might result
            qa_blocks = [f"Q:{block}".strip() for block in full_text.split("Q:") if block.strip()]

        if not qa_blocks:
            print("❌ RAG Error: No Q&A blocks found in the file. Make sure it's formatted correctly.")
            return

        print(f"Split document into {len(qa_blocks)} Q&A chunks.")
        
        # --- The rest of the function is the same ---
        print("Loading embedding model (this may take a moment on first run)...")
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        print("Creating FAISS vector store...")
        vector_store = FAISS.from_texts(qa_blocks, embeddings)

        _rag_retriever = vector_store.as_retriever(search_kwargs={"k": 1})
        
        print("✅ RAG service setup complete.")

    except FileNotFoundError:
        print(f"❌ RAG Error: The file '{file_path}' was not found.")
        _rag_retriever = None
    except Exception as e:
        print(f"❌ An unexpected error occurred during RAG setup: {e}")
        _rag_retriever = None

        
def query_rag(query: str) -> str:
    """
    Performs a similarity search on the vector store to find the most
    relevant document chunk for the user's query.

    Args:
        query (str): The user's question.

    Returns:
        The content of the most relevant document chunk, or a default
        message if no relevant information is found or RAG is not set up.
    """
    global _rag_retriever
    if _rag_retriever is None:
        return "Sorry, the FAQ information service is currently unavailable."

    try:
        # The retriever finds the most relevant documents (we set k=1, so it's just one)
        relevant_docs = _rag_retriever.invoke(query)
        
        if relevant_docs:
            # We return the text content of the first (and only) document
            return relevant_docs[0].page_content
        else:
            return "I couldn't find specific information about that in our FAQ. Please try rephrasing your question."
    except Exception as e:
        print(f"❌ RAG query failed: {e}")
        return "I'm having trouble accessing our information base right now. Please try again later."