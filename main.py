import sys
import os
import streamlit as st
from pathlib import Path
from io import BytesIO
import pandas as pd

# Ensure project root is on sys.path so local packages can be imported when
# running via `streamlit run main.py` or other entrypoints.
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from extractor.text_extractor import extract_text_from_file
except Exception as e:
    import traceback
    print('Failed to import extractor.text_extractor:', e)
    traceback.print_exc()
    raise

from section_detector.detector import detect_sections
from parsers.education_parser import parse_education
from parsers.experience_parser import parse_experience
from parsers.publication_parser import parse_publications
from validator.validator import compute_confidence, validate_extracted_data
from excel_generator.generator import generate_excels
from utils.helpers import extract_email, extract_phone, extract_name, extract_nationality, extract_country, extract_address, extract_orcid, extract_google_scholar
from parsers.simple_parsers import parse_awards, parse_memberships, parse_patents, parse_list_section
from llm.ollama_client import call_ollama
from llm.schema import validate_and_extract
import tempfile

st.set_page_config(page_title='Faculty Resume Evaluation System', layout='wide')

# Page title and description
st.title('📋 Faculty Resume Evaluation System')
st.markdown('Extract and analyze faculty information from resumes in bulk.')

# Initialize session state
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'result' not in st.session_state:
    st.session_state.result = None
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []

def log(msg):
    st.session_state.logs.append(msg)

# Advanced Settings Sidebar
with st.sidebar:
    st.header('⚙️ Advanced Settings')
    with st.expander('LLM & Extraction', expanded=False):
        enable_llm = st.checkbox('Enable Local LLM Fallback (Ollama)', value=False)
        force_llm = st.checkbox('Force LLM for all resumes', value=False)
        enable_debug = st.checkbox('Enable Debug Mode Reports', value=True)
        llm_attempts = st.number_input('LLM Attempts', min_value=1, max_value=10, value=3)
        llm_backoff = st.number_input('LLM Backoff Factor (sec)', min_value=0.0, max_value=10.0, value=1.0, step=0.5)
        llm_conf_threshold = st.slider('Confidence Threshold', min_value=0, max_value=100, value=60)
        ollama_host = st.text_input('Ollama Host', value='http://127.0.0.1:11434')
        ollama_model = st.text_input('Ollama Model', value='qwen2.5:7b-instruct')

    st.markdown('---')
    st.markdown('**About**')
    st.caption('Extract and organize faculty profile data from PDF and DOCX resumes.')

# Main Content Layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader('📤 Upload Resumes')
    uploaded_files = st.file_uploader(
        'Select one or more resume files (PDF, DOCX, DOC)',
        type=['pdf', 'docx', 'doc'],
        accept_multiple_files=True,
        key='uploader'
    )
    st.session_state.uploaded_files = uploaded_files or []

with col2:
    st.subheader('🚀 Process')
    process_button = st.button('Process Resumes', use_container_width=True, type='primary')


# Main processing pipeline
if process_button:
    if not st.session_state.uploaded_files:
        st.error('Please upload at least one resume file.')
    else:
        st.session_state.logs = []

        try:
            if os.path.exists('extraction_failures.log'):
                os.remove('extraction_failures.log')
            if os.path.exists('extraction_diagnostics.log'):
                os.remove('extraction_diagnostics.log')
        except Exception:
            pass

        entries = [('uploaded', f) for f in st.session_state.uploaded_files]
        total = len(entries)
        success = 0
        failed = 0
        master_rows = []
        pub_rows = []
        debug_emp_rows = []
        debug_pub_rows = []
        debug_val_rows = []
        debug_proc_rows = []

        # Progress tracking containers
        progress_bar = st.progress(0, text='Initializing...')
        status_text = st.empty()
        current_file_display = st.empty()

        for i, (etype, f) in enumerate(entries, start=1):
            name_display = f.name

            progress_pct = i / total if total > 0 else 1.0
            progress_bar.progress(progress_pct, text=f'Processing {i}/{total}')
            status_text.text(f'📄 {name_display}')

            try:
                # Handle uploaded file
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(f.name).suffix) as tmp:
                    tmp.write(f.read())
                    tmp_path = tmp.name

                text = extract_text_from_file(str(tmp_path))
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

                sections = detect_sections(text)
                field_errors = []

                # Personal details extraction with safety
                extracted_name_val = ""
                try:
                    extracted_name_val = extract_name(text)
                    if not extracted_name_val:
                        field_errors.append((name_display, 'Name', 'Name was not found in resume'))
                except Exception as e:
                    field_errors.append((name_display, 'Name', f'Exception: {e}'))

                personal = {
                    'Source File': name_display,
                    'Name': extracted_name_val,
                    'Email': '',
                    'Phone': '',
                    'Nationality': '',
                    'Country': '',
                    'Address': '',
                    'ORCID': '',
                    'Google Scholar': '',
                }

                try:
                    personal['Email'] = extract_email(text, name=extracted_name_val)
                    if not personal['Email']:
                        field_errors.append((name_display, 'Email', 'Email not found'))
                except Exception as e:
                    field_errors.append((name_display, 'Email', f'Exception: {e}'))

                try:
                    personal['Phone'] = extract_phone(text)
                    if not personal['Phone']:
                        field_errors.append((name_display, 'Phone', 'Phone not found'))
                except Exception as e:
                    field_errors.append((name_display, 'Phone', f'Exception: {e}'))

                try:
                    personal['Nationality'] = extract_nationality(text)
                except Exception as e:
                    field_errors.append((name_display, 'Nationality', f'Exception: {e}'))

                try:
                    personal['Country'] = extract_country(text)
                except Exception as e:
                    field_errors.append((name_display, 'Country', f'Exception: {e}'))

                try:
                    personal['Address'] = extract_address(text)
                except Exception as e:
                    field_errors.append((name_display, 'Address', f'Exception: {e}'))

                try:
                    personal['ORCID'] = extract_orcid(text)
                except Exception as e:
                    field_errors.append((name_display, 'ORCID', f'Exception: {e}'))

                try:
                    personal['Google Scholar'] = extract_google_scholar(text)
                except Exception as e:
                    field_errors.append((name_display, 'Google Scholar', f'Exception: {e}'))

                # Education details
                edu = {
                    "ug_degree": "", "ug_branch": "", "ug_university": "", "ug_institute": "", "ug_year": "",
                    "pg_degree": "", "pg_branch": "", "pg_university": "", "pg_institute": "", "pg_year": "",
                    "phd_university": "", "phd_institute": "", "phd_year": ""
                }
                try:
                    edu = parse_education(sections.get('education', ''))
                    if not edu.get('ug_degree'):
                        field_errors.append((name_display, 'UG Degree', 'UG Degree not found'))
                    if not edu.get('pg_degree') and not edu.get('phd_university'):
                        field_errors.append((name_display, 'PG/PhD Details', 'PG and PhD details not found'))
                except Exception as e:
                    field_errors.append((name_display, 'Education Section', f'Exception: {e}'))

                # Experience details
                exp = {
                    'summary': {
                        'Academic Experience': 0.0, 'Industry Experience': 0.0, 'Research Experience': 0.0, 'Administrative Experience': 0.0, 'Total Experience': 0.0,
                        'academic_years': 0.0, 'industry_years': 0.0, 'research_years': 0.0, 'admin_years': 0.0, 'total_years': 0.0
                    },
                    'current_designation': '', 'current_department': '', 'current_organization': '',
                    'jobs': []
                }
                try:
                    exp = parse_experience(sections.get('experience', ''), full_text=text)
                    if not exp.get('current_designation'):
                        field_errors.append((name_display, 'Current Designation', 'Current designation not found'))
                except Exception as e:
                    field_errors.append((name_display, 'Experience Section', f'Exception: {e}'))

                # Publications details
                pubs = {'counts': {}, 'publications': []}
                try:
                    pubs = parse_publications(sections.get('publications', ''))
                except Exception as e:
                    field_errors.append((name_display, 'Publications Section', f'Exception: {e}'))

                row = {
                    'Source File': name_display,
                    'Name': personal.get('Name', ''),
                    'Email': personal.get('Email', ''),
                    'Phone': personal.get('Phone', ''),
                    'Nationality': personal.get('Nationality', ''),
                    'Country': personal.get('Country', ''),
                    'Address': personal.get('Address', ''),
                    'UG Degree': edu.get('ug_degree', ''),
                    'UG Branch': edu.get('ug_branch', ''),
                    'UG University': edu.get('ug_university', ''),
                    'UG Institute': edu.get('ug_institute', ''),
                    'UG Year': edu.get('ug_year', ''),
                    'PG Degree': edu.get('pg_degree', ''),
                    'PG Branch': edu.get('pg_branch', ''),
                    'PG University': edu.get('pg_university', ''),
                    'PG Institute': edu.get('pg_institute', ''),
                    'PG Year': edu.get('pg_year', ''),
                    'PhD University': edu.get('phd_university', ''),
                    'PhD Institute': edu.get('phd_institute', ''),
                    'PhD Year': edu.get('phd_year', ''),
                    'ORCID': personal.get('ORCID', ''),
                    'Google Scholar': personal.get('Google Scholar', ''),
                }

                row.update(exp.get('summary', {}))

                pub_counts = pubs.get('counts', {})
                row['Journal Count'] = pub_counts.get('journal', 0)
                row['International Conference Count'] = pub_counts.get('int_conf', 0)
                row['National Conference Count'] = pub_counts.get('nat_conf', 0)
                row['Book Count'] = pub_counts.get('book', 0)
                row['Book Chapter Count'] = pub_counts.get('book_chapter', 0)

                # Lists details with try-except
                try:
                    patent_list = parse_patents(sections.get('patents', ''))
                    row['Patent Count'] = max(pub_counts.get('patent', 0), len(patent_list))
                except Exception as e:
                    field_errors.append((name_display, 'Patents Count', f'Exception: {e}'))
                    row['Patent Count'] = pub_counts.get('patent', 0)

                try:
                    projects_list = parse_list_section(sections.get('projects', ''))
                    row['Projects Count'] = len(projects_list)
                except Exception as e:
                    field_errors.append((name_display, 'Projects Count', f'Exception: {e}'))
                    row['Projects Count'] = 0

                try:
                    awards_list = parse_awards(sections.get('awards', ''))
                    row['Awards Count'] = len(awards_list)
                except Exception as e:
                    field_errors.append((name_display, 'Awards Count', f'Exception: {e}'))
                    row['Awards Count'] = 0

                try:
                    memberships_list = parse_memberships(sections.get('memberships', ''))
                    row['Membership Count'] = len(memberships_list)
                except Exception as e:
                    field_errors.append((name_display, 'Memberships Count', f'Exception: {e}'))
                    row['Membership Count'] = 0

                try:
                    fdp_sttp_list = parse_list_section(sections.get('fdp', ''))
                    fdp_count = 0
                    sttp_count = 0
                    for item in fdp_sttp_list:
                        if re.search(r'\b(?:sttp|short\s*term\s*training)\b', item.lower()):
                            sttp_count += 1
                        else:
                            fdp_count += 1
                    row['FDP Attended'] = fdp_count
                    row['STTP Attended'] = sttp_count
                except Exception as e:
                    field_errors.append((name_display, 'FDP/STTP Counts', f'Exception: {e}'))
                    row['FDP Attended'] = 0
                    row['STTP Attended'] = 0

                try:
                    row['Confidence Score'] = compute_confidence(personal, edu, exp, pubs)
                except Exception as e:
                    field_errors.append((name_display, 'Confidence Score', f'Exception: {e}'))
                    row['Confidence Score'] = 50

                try:
                    warnings = validate_extracted_data(personal, edu, exp, pubs)
                    row['Validation Warnings'] = "; ".join(warnings) if warnings else "None"
                except Exception as e:
                    field_errors.append((name_display, 'Validation Warnings', f'Exception: {e}'))
                    row['Validation Warnings'] = "None"

                # LLM fallback if enabled
                if enable_llm and (force_llm or row['Confidence Score'] < llm_conf_threshold):
                    try:
                        sec_edu = sections.get('education', '')[:1200]
                        sec_exp = sections.get('experience', '')[:1200]
                        sec_pubs = sections.get('publications', '')[:1200]
                        prompt = (
                            "You are an extraction assistant.\n"
                            "Return ONLY a single valid JSON object and nothing else.\n"
                            "Follow this schema: {name, email, phone, current_designation, current_department, current_organization, "
                            "education:{ug_degree,ug_branch,ug_university,ug_year,pg_degree,pg_branch,pg_university,pg_year,phd_university,phd_year}, "
                            "experience:{total_experience_years}, publications:[{type,title,journal,publisher,year}]}.\n"
                            "If a field is not present, return an empty string or empty array.\n"
                            "Sections:\n---EDUCATION---\n" + sec_edu + "\n---EXPERIENCE---\n" + sec_exp + "\n---PUBLICATIONS---\n" + sec_pubs
                        )
                        out = call_ollama(ollama_model, prompt, host=ollama_host, attempts=int(llm_attempts), backoff_factor=float(llm_backoff))
                        parsed = validate_and_extract(out)

                        if parsed.get('name'):
                            row['Name'] = parsed.get('name')
                        if parsed.get('email'):
                            row['Email'] = parsed.get('email')
                        if parsed.get('phone'):
                            row['Phone'] = parsed.get('phone')
                        ed = parsed.get('education', {})
                        for k in ['ug_degree', 'ug_branch', 'ug_university', 'ug_year', 'pg_degree', 'pg_branch', 'pg_university', 'pg_year', 'phd_university', 'phd_year']:
                            if ed.get(k):
                                row[k] = ed.get(k)
                        exp_parsed = parsed.get('experience', {})
                        if exp_parsed.get('total_experience_years'):
                            row['Total Experience'] = exp_parsed.get('total_experience_years')
                    except Exception as e:
                        log(f'LLM fallback failed for {name_display}: {str(e)[:50]}')

                master_rows.append(row)

                try:
                    for pub in pubs.get('publications', []):
                        pub_row = {
                            'Faculty Name': row.get('Name', ''),
                            'Designation': exp.get('current_designation', ''),
                            'Department': exp.get('current_department', ''),
                            'Publication Type': pub.get('type', ''),
                            'Title of Paper': pub.get('title', '') if pub.get('title') else pub.get('raw', ''),
                            'Journal Name': pub.get('journal_name', ''),
                            'Published Under / Publisher': pub.get('journal_details', '') if pub.get('journal_details') else pub.get('publisher', ''),
                            'Publisher': pub.get('publisher', 'Unknown'),
                            'Year of Publication': pub.get('year', ''),
                            'DOI': pub.get('doi', ''),
                            'ISSN / ISBN': pub.get('issn', ''),
                            'Scopus Indexed': pub.get('scopus_indexed', 'Unknown'),
                            'Source Resume': name_display,
                        }
                        pub_rows.append(pub_row)
                except Exception as e:
                    field_errors.append((name_display, 'Publications Rows Loop', f'Exception: {e}'))

                # Log failed fields details
                if field_errors:
                    try:
                        with open('extraction_failures.log', 'a', encoding='utf-8') as f_log:
                            for file_name, field_name, reason in field_errors:
                                f_log.write(f"File: {file_name} | Field: {field_name} | Reason: {reason}\n")
                    except Exception as e:
                        log(f"Warning: Failed to write to extraction_failures.log: {e}")

                # Log diagnostics for the resume
                try:
                    diag_sections = [k for k, v in sections.items() if v.strip()]
                    all_possible_sections = ['education', 'experience', 'publications', 'patents', 'projects', 'awards', 'memberships', 'fdp']
                    diag_missing = [s for s in all_possible_sections if not sections.get(s, '').strip()]
                    diag_parser = 'LLM (Fallback)' if (enable_llm and row['Confidence Score'] < llm_conf_threshold) else 'Regex/Rule-based Parsing Engine'
                    diag_reason = "None"
                    if row['Confidence Score'] < 75:
                        diag_reasons = []
                        if not personal.get('Email'): diag_reasons.append("Email missing")
                        if not personal.get('Phone'): diag_reasons.append("Phone missing")
                        if not edu.get('ug_degree'): diag_reasons.append("UG Degree missing")
                        if not exp.get('jobs'): diag_reasons.append("No job records found")
                        diag_reason = ", ".join(diag_reasons) if diag_reasons else "Low scoring profile"
                    
                    with open('extraction_diagnostics.log', 'a', encoding='utf-8') as f_diag:
                        f_diag.write("="*60 + "\n")
                        f_diag.write(f"Resume File: {name_display}\n")
                        f_diag.write(f"Extracted Sections: {', '.join(diag_sections) if diag_sections else 'None'}\n")
                        f_diag.write(f"Missing Sections: {', '.join(diag_missing) if diag_missing else 'None'}\n")
                        f_diag.write(f"Validation Warnings: {row.get('Validation Warnings', 'None')}\n")
                        f_diag.write(f"Parser Used: {diag_parser}\n")
                        f_diag.write(f"Confidence Score: {row['Confidence Score']}\n")
                        f_diag.write(f"Low Confidence Reason: {diag_reason}\n")
                        f_diag.write("="*60 + "\n\n")
                        
                    # Build and collect Debug Mode details
                    for item in exp.get('debug_employment', []):
                        item_with_file = {'Resume File': name_display}
                        item_with_file.update(item)
                        debug_emp_rows.append(item_with_file)
                        
                    for item in pubs.get('debug_publications', []):
                        item_with_file = {'Resume File': name_display}
                        item_with_file.update(item)
                        debug_pub_rows.append(item_with_file)
                        
                    val_report = {
                        'Resume File': name_display,
                        'Missing Fields': ", ".join(diag_missing) if diag_missing else "None",
                        'Warnings': row.get('Validation Warnings', 'None'),
                        'Validation Errors': "; ".join(warnings) if warnings else "None",
                        'Duplicate Detection': "Yes" if ("Duplicate" in row.get('Validation Warnings', '')) else "No",
                        'Confidence deductions': 100 - row['Confidence Score']
                    }
                    debug_val_rows.append(val_report)
                    
                    proc_report = {
                        'Resume File': name_display,
                        'Parser used': diag_parser,
                        'LLM response': st.session_state.get('last_llm_response', 'N/A'),
                        'Fallback parser used': "Yes" if diag_parser == 'LLM (Fallback)' else "No",
                        'Sections detected': ", ".join(diag_sections) if diag_sections else "None",
                        'Sections missing': ", ".join(diag_missing) if diag_missing else "None",
                        'Extraction confidence per field': f"Name: {100 if personal.get('Name') else 0}%, Email: {100 if personal.get('Email') else 0}%, Phone: {100 if personal.get('Phone') else 0}%, UG Degree: {100 if edu.get('ug_degree') else 0}%, PG Degree: {100 if edu.get('pg_degree') else 0}%, PhD Univ: {100 if edu.get('phd_university') else 0}%"
                    }
                    debug_proc_rows.append(proc_report)
                    
                    # Generate individual debug JSON in workspace
                    import json
                    individual_debug = {
                        'Employment History': exp.get('debug_employment', []),
                        'Publication Debug': pubs.get('debug_publications', []),
                        'Validation Report': val_report,
                        'Processing Report': proc_report
                    }
                    debug_file_path = f"debug_report_{Path(name_display).stem}.json"
                    with open(debug_file_path, 'w', encoding='utf-8') as f_debug_json:
                        json.dump(individual_debug, f_debug_json, indent=4)
                        
                except Exception as e:
                    log(f"Warning: Failed to collect debug details / write JSON: {e}")

                success += 1
                log(f'✓ {name_display}')
            except Exception as e:
                failed += 1
                log(f'✗ {name_display}: {str(e)[:50]}')

        # Generate Excel files
        # generate_excels returns (master_df: DataFrame, publication_wb: openpyxl Workbook)
        master_df, publication_wb = generate_excels(master_rows, pub_rows)

        # Build pubs_df from pub_rows for preview and flat download
        pubs_df = pd.DataFrame(pub_rows) if pub_rows else pd.DataFrame()

        # Create combined workbook (master sheet + per-faculty publication sheets)
        combined_buffer = BytesIO()
        with pd.ExcelWriter(combined_buffer, engine="openpyxl") as writer:
            master_df.to_excel(writer, sheet_name="Faculty Data", index=False)

            # Copy all publication sheets from the openpyxl workbook
            for ws in publication_wb.worksheets:
                new_sheet = writer.book.create_sheet(title=ws.title)
                for ws_row in ws.iter_rows(values_only=True):
                    new_sheet.append(ws_row)

        combined_bytes = combined_buffer.getvalue()

        # Generate Debug Excel Workbook if Debug Mode is enabled
        debug_bytes = None
        if enable_debug:
            try:
                debug_buffer = BytesIO()
                with pd.ExcelWriter(debug_buffer, engine="openpyxl") as d_writer:
                    emp_df = pd.DataFrame(debug_emp_rows) if debug_emp_rows else pd.DataFrame(columns=[
                        'Resume File', 'Organization', 'Designation', 'Department', 'Category', 'Start Date', 'End Date', 'Duration',
                        'Academic Contribution', 'Industry Contribution', 'Research Contribution', 'Administrative Contribution', 'Total Contribution'
                    ])
                    emp_df.to_excel(d_writer, sheet_name="Employment History", index=False)
                    
                    pub_df = pd.DataFrame(debug_pub_rows) if debug_pub_rows else pd.DataFrame(columns=[
                        'Resume File', 'Publication detected', 'Classification', 'Reason', 'Title', 'Publisher', 'Year', 'Confidence'
                    ])
                    pub_df.to_excel(d_writer, sheet_name="Publication Debug", index=False)
                    
                    val_df = pd.DataFrame(debug_val_rows) if debug_val_rows else pd.DataFrame(columns=[
                        'Resume File', 'Missing Fields', 'Warnings', 'Validation Errors', 'Duplicate Detection', 'Confidence deductions'
                    ])
                    val_df.to_excel(d_writer, sheet_name="Validation Report", index=False)
                    
                    proc_df = pd.DataFrame(debug_proc_rows) if debug_proc_rows else pd.DataFrame(columns=[
                        'Resume File', 'Parser used', 'Fallback parser used', 'Sections detected', 'Sections missing', 'Extraction confidence per field'
                    ])
                    proc_df.to_excel(d_writer, sheet_name="Processing Report", index=False)
                    
                debug_bytes = debug_buffer.getvalue()
            except Exception as e:
                log(f"Warning: Failed to generate Debug Excel Workbook: {e}")

        # Master Excel bytes (flat DataFrame)
        master_buffer = BytesIO()
        master_df.to_excel(master_buffer, index=False, engine='openpyxl')
        master_bytes = master_buffer.getvalue()

        # Publications Excel bytes (openpyxl workbook with per-faculty sheets)
        pubs_buffer = BytesIO()
        publication_wb.save(pubs_buffer)
        pubs_bytes = pubs_buffer.getvalue()

        st.session_state.result = {
            'total': total,
            'success': success,
            'failed': failed,
            'master_bytes': master_bytes,
            'pubs_bytes': pubs_bytes,
            'combined_bytes': combined_bytes,
            'debug_bytes': debug_bytes,
            'master_df': master_df,
            'pubs_df': pubs_df,
        }

        progress_bar.progress(1.0, text='Complete!')
        status_text.empty()

# Display results if processing completed
if st.session_state.result:
    result = st.session_state.result

    st.markdown('---')
    st.subheader('📊 Results Summary')

    # Statistics cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Total Resumes', result['total'])
    with col2:
        st.metric('Successfully Processed', result['success'], delta=result['total'] - result['success'] if result['failed'] > 0 else 0)
    with col3:
        st.metric('Failed', result['failed'])
    with col4:
        avg_conf = result['master_df']['Confidence Score'].mean() if not result['master_df'].empty else 0
        st.metric('Avg Confidence', f'{round(avg_conf, 1)}%')

    # Data previews
    st.markdown('---')
    st.subheader('📋 Data Preview')

    tab1, tab2 = st.tabs(['Faculty Data', 'Publications'])

    with tab1:
        st.dataframe(result['master_df'], use_container_width=True, height=300)

    with tab2:
        st.dataframe(result['pubs_df'], use_container_width=True, height=300)

    # Download buttons
    st.markdown('---')
    st.subheader('⬇️ Download Results')

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.download_button(
            label='📥 Master Excel',
            data=result['master_bytes'],
            file_name='master_faculty_database.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True
        )
    with col2:
        st.download_button(
            label='📥 Publications Excel',
            data=result['pubs_bytes'],
            file_name='publication_details.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True
        )
    with col3:
        st.download_button(
            label='📥 Combined Workbook',
            data=result['combined_bytes'],
            file_name='faculty_evaluation_report.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True
        )
    with col4:
        if result.get('debug_bytes'):
            st.download_button(
                label='📥 Debug Workbook',
                data=result['debug_bytes'],
                file_name='debug_evaluation_report.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True
            )
        else:
            st.button('📥 Debug Workbook (Disabled)', disabled=True, use_container_width=True)

    # Processing logs (collapsible)
    with st.expander('📝 Processing Logs', expanded=False):
        st.code('\n'.join(st.session_state.logs[-100:] or ['No logs available']), language='text')