import streamlit as st
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

def apply_custom_design():
    if os.path.exists("style.css"):
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def process_and_index(uploaded_file):
    try:
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        temp_file = f"temp_upload{file_ext}"
        
        with open(temp_file, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        if file_ext == ".pdf":
            loader = PyPDFLoader(temp_file)
        else:
            loader = TextLoader(temp_file)
            
        docs = loader.load()
      
        if os.path.exists(temp_file):
            os.remove(temp_file)

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=50)
        final_chunks = text_splitter.split_documents(docs)

        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(final_chunks, embeddings)
        return vectorstore
    except Exception as e:
        st.error(f"❌ Processing Error: {e}")
        return None


def main():
    apply_custom_design() 
    st.set_page_config(page_title="LOLA🎀", page_icon="⚡")
    st.title("⚡LOLA'S QA🎀 ")

    groq_key = os.getenv("GROQ_API_KEY")
    uploaded_file = st.file_uploader("Upload PDF or Text", type=["pdf", "txt"])

    if uploaded_file:
        if "vectorstore" not in st.session_state:
            with st.spinner("Indexing..."):
                st.session_state.vectorstore = process_and_index(uploaded_file)
        
        if st.session_state.vectorstore:
            st.success("Ready!")
            user_query = st.text_input("💬 Ask a question:")
            
            if user_query:
                try:
                    llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=groq_key)
                    
                    template = """You are a helpful assistant. Use the provided context to answer the question. 
                    If the answer isn't in the context, you may use your general knowledge to answer, 
                    but please mention that the information was not in the document.:
                    {context}
                    Question: {question}
                    """
                    prompt = ChatPromptTemplate.from_template(template)
                    retriever = st.session_state.vectorstore.as_retriever(search_kwargs={"k": 10})
                    
                    def format_docs(docs):
                        return "\n\n".join(doc.page_content for doc in docs)

                    rag_chain = (
                        {"context": retriever | format_docs, "question": RunnablePassthrough()}

                        | prompt
                        | llm
                        | StrOutputParser()
                    )

                    with st.spinner("Lola is thinking..."):
                        response = rag_chain.invoke(user_query)
                        st.markdown("### 💡 AI Answer:")
                        st.write(response)
                except Exception as e:
                    st.error(f"⚠️ AI Error: {e}")

if __name__ == "__main__":
    main()
