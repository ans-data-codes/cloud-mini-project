
import os
import streamlit as st
from supabase import create_client

st.set_page_config(
    page_title="CloudVault",
    page_icon="☁️",
    layout="centered"
)

st.title("☁️ CloudVault")
st.subheader("Cloud File Storage System")
st.write("Upload, store, and manage your files securely in the cloud.")

# Connect to Supabase
url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
BUCKET = "cloud-files"

if not url or not key:
    st.error("Please configure your Supabase credentials.")
    st.stop()

try:
    supabase = create_client(url, key)
except Exception:
    st.error("Could not connect to Supabase.")
    st.stop()

# Upload section
st.header("📤 Upload Files")
uploaded_file = st.file_uploader("Choose a file")

if uploaded_file:
    st.write(f"**File:** {uploaded_file.name}")
    st.write(f"**Size:** {uploaded_file.size:,} bytes")

    if st.button("Upload to Cloud"):
        try:
            supabase.storage.from_(BUCKET).upload(
                path=uploaded_file.name,
                file=uploaded_file.getvalue(),
                file_options={
                    "upsert": "true",
                    "content-type": uploaded_file.type
                    or "application/octet-stream"
                }
            )
            st.success("File uploaded successfully!")
        except Exception as e:
            st.error(f"Upload failed: {e}")

# Stored files section
st.header("📁 Stored Files")

if st.button("Refresh File List"):
    st.rerun()

try:
    files = supabase.storage.from_(BUCKET).list()

    if not files:
        st.info("No files stored yet.")

    for file in files:
        name = file.get("name", "")

        if not name:
            continue

        with st.container(border=True):
            st.write(f"📄 **{name}**")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Download", key=f"download_{name}"):
                    try:
                        data = supabase.storage.from_(BUCKET).download(name)
                        st.download_button(
                            "Save File",
                            data=data,
                            file_name=name,
                            key=f"save_{name}"
                        )
                    except Exception as e:
                        st.error(f"Download failed: {e}")

            with col2:
                if st.button("Delete", key=f"delete_{name}"):
                    try:
                        supabase.storage.from_(BUCKET).remove([name])
                        st.success("File deleted successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")

except Exception as e:
    st.error(f"Could not retrieve files: {e}")
