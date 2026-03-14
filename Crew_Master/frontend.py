import streamlit as st
import requests
import os

# Title
st.title("Crew Scheduling Application")

# File uploader (Excel only)
uploaded_file = st.file_uploader("Upload Sector and Crew Data (Excel file)", type=["xlsx"])

# API endpoint (replace with your actual API URL)
API_URL = "http://127.0.0.1:8000/crew"

# Path where you want to store uploaded files
SAVE_DIR = "uploaded_files"
os.makedirs(SAVE_DIR, exist_ok=True)

if uploaded_file is not None:
    st.write("File uploaded successfully!")

    # Show file details
    st.write("Filename:", uploaded_file.name)

    # Save file locally
    save_path = os.path.join(SAVE_DIR, uploaded_file.name)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"File saved at {save_path}")

    # Button to send file to API
    if st.button("Validate and Schedule"):
        try:
            with open(save_path, "rb") as f:
                files = {"file": f}
                response = requests.post(API_URL, files=files)
            if response.status_code == 200:
                st.success("Scheduling successful!")
                #st.write("Response:", response.json())
                # Save response content locally
                output_path = os.path.join("downloaded", f"FinalSchedule_Latest_Roster")
                os.makedirs("downloaded", exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.content)

                # Provide download button
                with open(output_path, "rb") as f:
                    st.download_button(
                        label="Download Crew Schedule/Roaster",
                        data=f,
                        file_name=f"FinalSchedule_Latest_Roster.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error(f"API call failed with status code {response.status_code}")
                st.write(response.text)
        except Exception as e:
            st.error(f"Error calling API: {e}")