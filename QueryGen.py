import pandas as pd
import streamlit as st
from openai import OpenAI
import os
from io import BytesIO
import xlsxwriter


# Load your API key from Streamlit secrets
api_key = st.secrets["OPENAI_API_KEY"]

if not api_key:
    st.error("API key not found. Please set the OPENAI_API_KEY in Streamlit secrets.")
else:
    client = OpenAI(api_key=api_key)

    def chat_gpt(prompt):
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    def read_etl_mapping(file_path):
        return pd.read_excel(file_path)

    def read_prompt_template(file_path):
        with open(file_path, 'r') as file:
            return file.read()

    def construct_prompt(etl_mapping_df, prompt_template):
        prompt = prompt_template + "\n\nETL Mapping Document:\n"
        for _, row in etl_mapping_df.iterrows():
            prompt += f"{row['Stage Table']} | {row['Source Column']} | {row['Target Table']} | {row['Target Column']} | {row['Transformation']}\n"
        return prompt

    def generate_validation_sql(prompt_template, etl_mapping_content):
        prompt = prompt_template + "\n\n" + etl_mapping_content
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates SQL validation queries from ETL mapping documents."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()

    # Streamlit UI
    st.title("ETL Mapping to Validation SQL Converter")

    st.write("Upload your ETL mapping Excel document below:")

    uploaded_file = st.file_uploader("Choose a file", type="xlsx")

    if uploaded_file is not None:
        try:
            etl_mapping_df = read_etl_mapping(uploaded_file)
            prompt_template_path = os.path.join(os.path.dirname(__file__), 'prompt_template.txt')
            prompt_template = read_prompt_template(prompt_template_path)

            st.write("ETL Mapping Document:")
            st.dataframe(etl_mapping_df)
        except Exception as e:
            st.error(f"Error reading uploaded file: {e}")

    if st.button("Generate Validation SQL"):
        with st.spinner("Generating SQL..."):
            try:
                # Check if etl_mapping_df is defined and valid
                if 'etl_mapping_df' not in locals() or etl_mapping_df.empty:
                    st.error("ETL Mapping data is not loaded or is empty.")
                else:
                    # Construct prompt and generate validation SQL
                    etl_mapping_content = construct_prompt(etl_mapping_df, prompt_template)
                    validation_sql = generate_validation_sql(prompt_template, etl_mapping_content)

                    # Display the generated SQL
                    st.subheader("Generated Validation SQL")
                    st.code(validation_sql, language="sql")

                    # Prepare DataFrame for exporting to Excel
                    sql_df = pd.DataFrame({"Generated SQL": [validation_sql]})

                    # Convert DataFrame to Excel in memory
                    excel_file = BytesIO()
                    with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
                        sql_df.to_excel(writer, index=False, sheet_name='Validation SQL')
                    excel_file.seek(0)

                    # Provide download button
                    st.download_button(
                        label="Download Validation SQL as Excel",
                        data=excel_file,
                        file_name="validation_sql.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"An error occurred during SQL generation: {e}")
