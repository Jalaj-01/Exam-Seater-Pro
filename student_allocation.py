import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
import math
import json
import pdfplumber

# Custom imports for user management and auth
import db_helper
import auth_helper

# --- PAGE CONFIGURATION (FIRST STREAMLIT COMMAND) ---
st.set_page_config(page_title="OptiSeat - Smart Seating System", layout="wide")

# --- INITIALIZE SESSION STATE ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'landing'
if 'plans' not in st.session_state:
    st.session_state.plans = None
if 'leftovers' not in st.session_state:
    st.session_state.leftovers = 0

# --- GOOGLE OAUTH CALLBACK HANDLER ---
query_params = st.query_params
if "code" in query_params:
    code = query_params["code"]
    user_info = auth_helper.get_user_info_from_code(code)
    if user_info and "email" in user_info:
        email = user_info["email"]
        name = user_info.get("name", email.split("@")[0].title())
        picture = user_info.get("picture", "")
        
        # Register user in DB (updates if already exists)
        db_helper.register_user(email, name, picture)
        db_helper.log_activity(email, "Login", "Google OAuth Login")
        
        # Save to session state
        st.session_state.user = db_helper.get_user(email)
        
        # Determine routing path
        if db_helper.is_user_onboarded(email):
            st.session_state.current_page = 'app'
        else:
            st.session_state.current_page = 'onboarding'
        
        # Clear params and rerun
        st.query_params.clear()
        st.rerun()

# --- PREMIUM GLOBAL STYLING CSS ---
st.markdown("""
<style>
/* ===== GLOBAL RESET & COMPONENT SPACING ===== */
.block-container {
    padding-top: 1.5rem !important;
    margin-top: 0rem !important;
}

[data-testid="stHeader"] {
    background: rgba(0,0,0,0);
}

section[data-testid="stSidebar"] {
    padding-top: 0.5rem !important;
}

[data-testid="stSidebarUserContent"] {
    padding-top: 1rem !important;
}

[data-testid="stFileUploader"] {
    margin-top: 8px;
    margin-bottom: 12px;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ===== APP BRAND HEADER ===== */
.header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 24px;
    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
    border-radius: 12px;
    margin-bottom: 24px;
    color: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.logo-text {
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: -0.5px;
}

.tagline-text {
    font-size: 0.85rem;
    color: #9ca3af;
}

/* ===== SEATING CARDS ===== */
.seat-card {
    margin: 6px;
    border: 2px solid;
    border-radius: 12px;
    padding: 8px;
    text-align: center;
    background: white;
    min-height: 95px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0px 2px 6px rgba(0,0,0,0.05);
}

.seat-card:hover {
    transform: scale(1.05);
    z-index: 10;
    position: relative;
    box-shadow: 0px 8px 20px rgba(0,0,0,0.15);
    cursor: pointer;
}

.seat-pos {
    font-size: 0.7em;
    color: #9ca3af;
}

.seat-id {
    font-weight: bold;
}

.seat-paper {
    font-size: 0.75em;
    padding: 2px 6px;
    border-radius: 6px;
}

.empty-seat {
    border: 1px dashed #ddd;
    border-radius: 12px;
    min-height: 95px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #aaa;
    font-size: 0.8rem;
    background-color: #fafafa;
}

/* ===== SIDEBAR PROFILE BOX ===== */
.profile-box {
    background-color: #f3f4f6;
    padding: 12px;
    border-radius: 10px;
    margin-bottom: 16px;
    border: 1px solid #e5e7eb;
}

.profile-name {
    font-weight: 600;
    font-size: 0.95rem;
    color: #1f2937;
    margin-bottom: 2px;
}

.profile-email {
    font-size: 0.8rem;
    color: #6b7280;
    margin-bottom: 6px;
    word-break: break-all;
}

.profile-institute {
    font-size: 0.75rem;
    color: #4f46e5;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# --- HELPER TO HANDLE MULTIPLE FORMATS ---
def load_data(uploaded_file):
    if uploaded_file is None:
        return None
    
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    try:
        if file_extension in ['xlsx', 'xls']:
            return pd.read_excel(uploaded_file)
        elif file_extension in ['csv', 'txt']:
            return pd.read_csv(uploaded_file)
        elif file_extension == 'json':
            return pd.read_json(uploaded_file)
        elif file_extension == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                all_rows = []
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        all_rows.extend(table)
                if not all_rows:
                    st.error(f"No tables found in {uploaded_file.name}")
                    return pd.DataFrame()
                df = pd.DataFrame(all_rows[1:], columns=all_rows[0])
                return df
    except Exception as e:
        st.error(f"Error loading {uploaded_file.name}: {e}")
        return None

# --- CORE ALLOCATION ALGORITHM ---
def allocate_logic(df_students, rooms_list):
    paper_data = df_students.groupby('PaperCode')['RollNo'].apply(list).to_dict()
    all_room_plans = {}
    
    for _, room in rooms_list.iterrows():
        if sum(len(s) for s in paper_data.values()) == 0:
            break
            
        r, c = int(room['Rows']), int(room['Cols'])
        grid = [[None for _ in range(c)] for _ in range(r)]
        has_students = False
        
        for i in range(r):
            for j in range(c):
                illegal = set()
                if j > 0 and grid[i][j-1]: illegal.add(grid[i][j-1]['paper'])
                if i > 0 and grid[i-1][j]: illegal.add(grid[i-1][j]['paper'])

                safe_papers = [p for p, stds in paper_data.items() if len(stds) > 0 and p not in illegal]
                if safe_papers:
                    best_p = max(safe_papers, key=lambda p: len(paper_data[p]))
                    grid[i][j] = {'id': paper_data[best_p].pop(0), 'paper': best_p}
                    has_students = True
        
        if has_students:
            all_room_plans[room['RoomName']] = grid
            
    leftovers = sum(len(stds) for stds in paper_data.values())
    return all_room_plans, leftovers

# --- PDF GENERATOR CLASS ---
class ExamPDF(FPDF):
    def set_exam_details(self, date, time):
        self.exam_date = date
        self.exam_time = time

    def header(self):
        try: self.set_font('Arial', 'B', 15)
        except: self.set_font('Helvetica', 'B', 15)
        self.cell(0, 10, 'COLLEGE EXAMINATION AUTHORITY', 0, 1, 'C')
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 10, f'DATE: {self.exam_date} | TIME: {self.exam_time}', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        try: self.set_font('Arial', 'I', 8)
        except: self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'© Copyright - Jalaj Gupta | Page {self.page_no()}', 0, 0, 'C')

def create_pdf(room_plans, assignments, exam_date, exam_time):
    pdf = ExamPDF()
    pdf.set_exam_details(exam_date, exam_time)
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, "MASTER SEATING INDEX (Sorted for Students)", 0, 1, 'C')
    pdf.ln(5)
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(35, 10, "Roll Number", 1, 0, 'C', True)
    pdf.cell(35, 10, "Paper", 1, 0, 'C', True)
    pdf.cell(35, 10, "Room", 1, 0, 'C', True)
    pdf.cell(30, 10, "Seat No", 1, 0, 'C', True)
    pdf.cell(55, 10, "Signature", 1, 1, 'C', True)
    
    master_list = []
    for room_name, grid in room_plans.items():
        for r_idx, row in enumerate(grid):
            for c_idx, seat in enumerate(row):
                if seat:
                    master_list.append({
                        'RollNo': str(seat['id']), 
                        'Paper': seat['paper'], 
                        'Room': room_name, 
                        'Seat': f"R{r_idx+1}C{c_idx+1}"
                    })
    master_list.sort(key=lambda x: x['RollNo'])
    pdf.set_font('Helvetica', '', 10)
    for entry in master_list:
        if pdf.get_y() > 260:
            pdf.add_page()
            pdf.set_fill_color(200, 220, 255)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(35, 10, "Roll Number", 1, 0, 'C', True)
            pdf.cell(35, 10, "Paper", 1, 0, 'C', True)
            pdf.cell(35, 10, "Room", 1, 0, 'C', True)
            pdf.cell(30, 10, "Seat No", 1, 0, 'C', True)
            pdf.cell(55, 10, "Signature", 1, 1, 'C', True)
            pdf.set_font('Helvetica', '', 10)
        pdf.cell(35, 10, entry['RollNo'], 1, 0, 'C')
        pdf.cell(35, 10, entry['Paper'], 1, 0, 'C')
        pdf.cell(35, 10, entry['Room'], 1, 0, 'C')
        pdf.cell(30, 10, entry['Seat'], 1, 0, 'C')
        pdf.cell(55, 10, "", 1, 1)

    for room_name, grid in room_plans.items():
        room_total = sum(1 for row in grid for seat in row if seat)
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 10, f"OFFICIAL ATTENDANCE SHEET: {room_name}", 0, 1)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 8, f"TOTAL STUDENTS IN ROOM: {room_total}", 0, 1)
        pdf.set_font('Helvetica', 'I', 10)
        
        teacher_assigned = assignments.get(room_name, ["N/A"])[0]
        pdf.cell(0, 8, f"Invigilator: {teacher_assigned}", 0, 1)
        pdf.ln(5)
        pdf.set_fill_color(200, 220, 255)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(25, 10, "Seat", 1, 0, 'C', True)
        pdf.cell(45, 10, "Roll Number", 1, 0, 'C', True)
        pdf.cell(40, 10, "Paper", 1, 0, 'C', True)
        pdf.cell(80, 10, "Signature", 1, 1, 'C', True)
        pdf.set_font('Helvetica', '', 11)
        for r_idx, row in enumerate(grid):
            for c_idx, seat in enumerate(row):
                if seat:
                    pdf.cell(25, 12, f"R{r_idx+1}C{c_idx+1}", 1, 0, 'C')
                    pdf.cell(45, 12, str(seat['id']), 1, 0, 'C')
                    pdf.cell(40, 12, str(seat['paper']), 1, 0, 'C')
                    pdf.cell(80, 12, "", 1, 1)
    
    return pdf.output(dest="S").encode("latin-1")

def create_sample_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


# =========================================================================
# PAGE: LANDING PAGE
# =========================================================================
def show_landing_page():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding: 3.5rem; border-radius: 20px; color: white; text-align: center; margin-bottom: 2.5rem; box-shadow: 0 10px 30px rgba(79,70,229,0.25);">
      <h1 style="font-size: 3.2rem; font-weight: 800; margin-bottom: 0.8rem; letter-spacing: -1px; line-height: 1;">🎓 OptiSeat</h1>
      <p style="font-size: 1.25rem; max-width: 750px; margin: 0 auto 2.5rem auto; opacity: 0.9; font-weight: 300;">
        Smart Examination Seating and Faculty Allocation System. Construct space-optimized, conflict-free layouts, assign invigilators, and generate ready-to-print index documents instantly.
      </p>
    </div>
    """, unsafe_allow_html=True)
    
    col_feat, col_login = st.columns([5, 4], gap="large")
    
    with col_feat:
        st.markdown("### Why Choose OptiSeat?")
        
        features = [
            ("⚡", "Automated Seating Algorithm", "Instantly allocates students to seating matrices while strictly avoiding adjacent seating of same-subject students to minimize cheating risk."),
            ("👨‍🏫", "Equitable Invigilation Rotations", "Distributes exam invigilation responsibilities dynamically based on previous assignments to keep workload fair."),
            ("📄", "Multi-format Import / Export", "Supports parsing student lists from PDF, Excel, CSV, or JSON. Download master layouts and attendance sheets as structured PDFs."),
            ("🔍", "Interactive Search Map", "Quickly find any student's room and seat coordinates with real-time grid highlighting.")
        ]
        
        for icon, title, desc in features:
            st.markdown(f"""
            <div style="display: flex; align-items: flex-start; margin-bottom: 20px;">
                <div style="font-size: 1.8rem; margin-right: 15px; margin-top: 2px;">{icon}</div>
                <div>
                    <h5 style="margin: 0; font-weight: 600; color: #1f2937;">{title}</h5>
                    <p style="margin: 2px 0 0 0; color: #6b7280; font-size: 0.9rem;">{desc}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    with col_login:
        st.markdown("<div style='padding: 24px; border-radius: 16px; border: 1px solid #e5e7eb; background-color: #fafafb; box-shadow: 0 4px 6px rgba(0,0,0,0.02);'>", unsafe_allow_html=True)
        st.subheader("🚪 System Authentication")
        
        if auth_helper.is_oauth_configured():
            st.markdown("Authenticate using your Google identity to access the system dashboard.")
            st.markdown("<br>", unsafe_allow_html=True)
            st.link_button(
                "🔑 Sign In with Google", 
                auth_helper.get_google_auth_url(), 
                type="primary", 
                use_container_width=True
            )
        else:
            st.info("💡 **Google OAuth credentials are not configured.** Running in Developer Sandbox Mode.")
            
            sandbox_email = st.text_input("Enter Email Address (use jalajgupta550@gmail.com for admin access):")
            sandbox_name = st.text_input("Enter Name (Optional):")
            
            if st.button("Sign In (Sandbox Sim)", type="primary", use_container_width=True):
                if sandbox_email:
                    # Retrieve or create profile simulation
                    user_profile = auth_helper.simulate_login(sandbox_email, sandbox_name)
                    email = user_profile["email"]
                    
                    db_helper.register_user(email, user_profile["name"], user_profile["picture"])
                    db_helper.log_activity(email, "Login", "Sandbox Login Simulation")
                    
                    st.session_state.user = db_helper.get_user(email)
                    
                    if db_helper.is_user_onboarded(email):
                        st.session_state.current_page = 'app'
                    else:
                        st.session_state.current_page = 'onboarding'
                    st.rerun()
                else:
                    st.error("Please enter a valid email to test the login flow.")
                    
        st.markdown("</div>", unsafe_allow_html=True)


# =========================================================================
# PAGE: ONBOARDING SYSTEM
# =========================================================================
def show_onboarding_page():
    user = st.session_state.user
    st.markdown(f"""
    <div style="background-color: #f8fafc; padding: 2.5rem; border-radius: 16px; border: 1px solid #e2e8f0; max-width: 800px; margin: 2rem auto; box-shadow: 0 10px 25px rgba(0,0,0,0.03);">
        <h2 style="margin: 0; color: #1e293b; font-weight: 800;">Welcome to OptiSeat, {user['name']}!</h2>
        <p style="color: #64748b; margin-top: 4px; margin-bottom: 2rem;">Please provide your institution profile and contact details to finalize registration.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("onboarding_form"):
        st.markdown("<div style='max-width: 800px; margin: 0 auto;'>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            institute_name = st.text_input("Institute / University Name*", placeholder="e.g. Stanford University")
        with col2:
            school_email = st.text_input("Official College/Institute Email*", value=user['email'], placeholder="e.g. j.gupta@mit.edu")
            
        address = st.text_area("Institute Address*", placeholder="e.g. 450 Serra Mall, Stanford, CA 94305")
        
        st.markdown("<p style='color: gray; font-size: 0.8rem; margin-top: 15px;'>* Indicates required fields</p>", unsafe_allow_html=True)
        submit = st.form_submit_button("Complete Registration", type="primary")
        
        if submit:
            if not institute_name or not school_email or not address:
                st.error("All required fields must be completed.")
            else:
                db_helper.update_onboarding(user['email'], school_email, institute_name, address)
                db_helper.log_activity(user['email'], "Onboarded", f"Institute: {institute_name}, Email: {school_email}")
                
                # Refresh session state
                st.session_state.user = db_helper.get_user(user['email'])
                st.session_state.current_page = 'app'
                st.success("Registration complete!")
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)


# =========================================================================
# PAGE: ADMIN SYSTEM CONTROL
# =========================================================================
def show_admin_page():
    user = st.session_state.user
    if not user or user["email"] != "jalajgupta550@gmail.com":
        st.error("Access Denied: Administrative privileges required.")
        if st.button("Return to Planner Dashboard"):
            st.session_state.current_page = 'app'
            st.rerun()
        st.stop()
        
    st.markdown("""
    <div class="header-bar">
        <div>
            <span class="logo-text">🛠️ OptiSeat Admin Panel</span>
            <span class="tagline-text">&nbsp;|&nbsp; Control Center & Logs</span>
        </div>
        <div>
            <span style="font-size: 0.9rem; color: #10b981; font-weight:600; padding: 4px 10px; border-radius: 20px; background: rgba(16,185,129,0.1);">Admin Account</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # FETCH DB STATS
    stats = db_helper.get_stats()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Total Users Registered", stats["total_users"])
    c2.metric("🏫 Onboarded Institutions", stats["onboarded_users"])
    c3.metric("📈 Total Actions Logged", stats["total_logs"])
    c4.metric("🔥 Active Users Today", stats["active_today"])
    
    st.markdown("---")
    
    tab_users, tab_logs = st.tabs(["👥 Users Directory", "📋 Real-Time Activity Logs"])
    
    with tab_users:
        st.subheader("Registered Users")
        users_list = db_helper.get_all_users()
        if users_list:
            df_users = pd.DataFrame(users_list)
            # Reorder for presentation
            cols = ["name", "email", "school_email", "institute_name", "address", "created_at"]
            df_users = df_users[cols]
            df_users.columns = ["Name", "Google Email", "Institution Email", "Institution Name", "Address", "Registered Date"]
            
            search_u = st.text_input("🔍 Search users by name or institute", "")
            if search_u:
                df_users = df_users[
                    df_users["Name"].str.contains(search_u, case=False, na=False) | 
                    df_users["Institution Name"].str.contains(search_u, case=False, na=False) | 
                    df_users["Google Email"].str.contains(search_u, case=False, na=False)
                ]
            st.dataframe(df_users, use_container_width=True)
        else:
            st.info("No registered users found.")
            
    with tab_logs:
        st.subheader("Audit Trail logs")
        logs_list = db_helper.get_activity_logs(limit=150)
        if logs_list:
            df_logs = pd.DataFrame(logs_list)
            cols_l = ["timestamp", "name", "email", "action", "details"]
            df_logs = df_logs[cols_l]
            df_logs.columns = ["Timestamp", "Name", "Email Address", "User Action", "Action Details"]
            
            search_l = st.text_input("🔍 Search logs by user or action", "")
            if search_l:
                df_logs = df_logs[
                    df_logs["Name"].str.contains(search_l, case=False, na=False) | 
                    df_logs["Email Address"].str.contains(search_l, case=False, na=False) | 
                    df_logs["User Action"].str.contains(search_l, case=False, na=False) | 
                    df_logs["Action Details"].str.contains(search_l, case=False, na=False)
                ]
            st.dataframe(df_logs, use_container_width=True)
        else:
            st.info("No activity logs recorded yet.")


# =========================================================================
# PAGE: SEATING ARRANGEMENT WORKSPACE (MAIN APP)
# =========================================================================
def show_main_app():
    user = st.session_state.user
    
    st.markdown(f"""
    <div class="header-bar">
        <div>
            <span class="logo-text">🎓 OptiSeat</span>
            <span class="tagline-text">&nbsp;|&nbsp; Smart Exam Seating Workspace</span>
        </div>
        <div style="font-size: 0.9rem; color: #9ca3af;">
            Welcome, <b>{user['name']}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- SESSION STATE ---
    if 'plans' not in st.session_state:
        st.session_state.plans = None
        st.session_state.leftovers = 0

    # --- SIDEBAR PANELS ---
    # Display user card in sidebar
    st.sidebar.markdown(f"""
    <div class="profile-box">
        <div class="profile-name">👤 {user['name']}</div>
        <div class="profile-email">{user['email']}</div>
        <div class="profile-institute">🏢 {user.get('institute_name', 'N/A')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation Links
    if user['email'] == "jalajgupta550@gmail.com":
        if st.sidebar.button("🛠️ Admin Control Panel", use_container_width=True):
            st.session_state.current_page = 'admin'
            st.rerun()
            
    if st.sidebar.button("🚪 Sign Out / Exit", use_container_width=True):
        db_helper.log_activity(user['email'], "Logout", "Manual session termination")
        st.session_state.user = None
        st.session_state.plans = None
        st.session_state.leftovers = 0
        st.session_state.current_page = 'landing'
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📂 Data Upload Panel")

    with st.sidebar.expander("🛠️ Need Test Files?"):
        s_df = pd.DataFrame({
            'RollNo': [f'STU{1000 + i}' for i in range(250)], 
            'PaperCode': (['CS101']*180 + ['MA202']*70), 
            'ExamDate': (['2026-02-10']*250),
            'ExamTime': (['09:00 AM']*250)
        })
        r_df = pd.DataFrame({'RoomName': [f'ROOM-{i}' for i in range(1, 15)], 'Rows': [6]*14, 'Cols': [6]*14})
        f_df = pd.DataFrame({'Name': [f'Faculty-{i}' for i in range(1, 10)], 'DutiesDone': [0]*9})
        
        st.download_button("Download Students.xlsx", create_sample_excel(s_df), "students.xlsx")
        st.download_button("Download Rooms.xlsx", create_sample_excel(r_df), "rooms.xlsx")
        st.download_button("Download Faculty.xlsx", create_sample_excel(f_df), "faculty.xlsx")

    # --- FILE UPLOADERS ---
    allowed_types = ['xlsx', 'xls', 'csv', 'json', 'pdf', 'txt']

    file_students = st.sidebar.file_uploader("Upload Student List", type=allowed_types)
    file_rooms = st.sidebar.file_uploader("Upload Room Details", type=allowed_types)
    file_faculty = st.sidebar.file_uploader("Upload Faculty List", type=allowed_types)

    # --- MAIN LOGIC ---
    if not (file_students and file_rooms and file_faculty):
        st.markdown(":green[**Ready to help! Please upload your data files in the sidebar.**]")

        st.markdown("### **Required Columns in Templates:**")
        st.markdown("""
        *   **Students File:** `RollNo` , `PaperCode`, `ExamDate`, `ExamTime`
        *   **Rooms File:** `RoomName` , `Rows` , `Cols`
        *   **Faculty File:** `Name` , `DutiesDone`
        """)
    else:
        df_st = load_data(file_students)
        df_rm = load_data(file_rooms)
        df_fa = load_data(file_faculty)

        if df_st is not None and df_rm is not None and df_fa is not None:
            # DASHBOARD STATS
            total_students = len(df_st)
            total_rooms = len(df_rm)
            total_subjects = df_st['PaperCode'].nunique() if 'PaperCode' in df_st.columns else 0
            total_faculty = len(df_fa)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🎓 Total Students Uploaded", total_students)
            col2.metric("🏫 Total Rooms Configured", total_rooms)
            col3.metric("📚 Subjects / Papers", total_subjects)
            col4.metric("👨‍🏫 Registered Faculty", total_faculty)

            st.markdown("---")

            if 'ExamDate' in df_st.columns and 'ExamTime' in df_st.columns:
                df_st['ExamDate'] = df_st['ExamDate'].astype(str)
                df_st['ExamTime'] = df_st['ExamTime'].astype(str)

                dates = sorted(df_st['ExamDate'].unique())
                col_d, col_t = st.columns(2)

                selected_date = col_d.selectbox("📅 Select Exam Date", dates)
                times = sorted(df_st[df_st['ExamDate'] == selected_date]['ExamTime'].unique())
                selected_time = col_t.selectbox("🕒 Select Exam Time/Shift", times)

                day_students = df_st[(df_st['ExamDate'] == selected_date) & (df_st['ExamTime'] == selected_time)]
                student_count = len(day_students)

                paper_counts = day_students['PaperCode'].value_counts()
                max_s = paper_counts.max() if not paper_counts.empty else 0
                required_physical_seats = max(student_count, (2 * max_s) - 1)

                df_rm['Rows'] = pd.to_numeric(df_rm['Rows'])
                df_rm['Cols'] = pd.to_numeric(df_rm['Cols'])
                df_rm['Capacity'] = df_rm['Rows'] * df_rm['Cols']
                total_capacity = df_rm['Capacity'].sum()

                st.info(f"**Status for {selected_date} ({selected_time}):** {student_count} students taking {day_students['PaperCode'].nunique()} subjects.")

                if st.session_state.plans:
                    rooms_display = len(st.session_state.plans)
                    label = "Rooms Actually Used"
                else:
                    rooms_needed = 0
                    running_cap = 0
                    for _, rm in df_rm.sort_values(by='Capacity', ascending=False).iterrows():
                        if running_cap < required_physical_seats:
                            running_cap += rm['Capacity']
                            rooms_needed += 1
                    rooms_display = rooms_needed
                    label = "Rooms Accurate Est. Required"

                c1, c2, c3 = st.columns(3)
                c1.metric("Total Physical Chairs", total_capacity)
                c2.metric(label, f"{rooms_display} / {len(df_rm)}")

                if required_physical_seats > total_capacity:
                    c3.error(f"⚠️ Gap Shortage: {required_physical_seats - total_capacity} extra seats needed")
                else:
                    c3.success(f"✅ Safe Spacing: {total_capacity - required_physical_seats} surplus seats")

                if st.button("🚀 Generate Arrangement", type="primary"):
                    st.session_state.plans, st.session_state.leftovers = allocate_logic(day_students.copy(), df_rm)
                    # Log activity
                    db_helper.log_activity(
                        user['email'], 
                        "Generate Seating", 
                        f"Arranged seating for date: {selected_date}, shift: {selected_time}. Total students: {student_count}."
                    )
                    st.rerun()

                if st.session_state.plans:
                    plans = st.session_state.plans
                    assignments = {}

                    temp_fa = df_fa.copy()
                    if 'DutiesDone' in temp_fa.columns:
                        temp_fa['DutiesDone'] = pd.to_numeric(temp_fa['DutiesDone'])
                    else:
                        temp_fa['DutiesDone'] = 0

                    for room_name, grid in plans.items():
                        temp_fa = temp_fa.sort_values(by='DutiesDone')
                        chosen_teacher = temp_fa.iloc[0]['Name'] if not temp_fa.empty else "No Faculty Available"
                        if not temp_fa.empty:
                            temp_fa.at[temp_fa.index[0], 'DutiesDone'] += 1
                        assignments[room_name] = [chosen_teacher]
                    
                    search_roll = st.text_input("🔍 Search Student by Roll Number")
                   
                    # Highlight coordinates tracker
                    found_flag = False
                    found_room = None
                    result_placeholder = st.empty()
                    
                    st.markdown("---")
                    st.header("🪑 Room Visualizations")
                    
                    room_names = list(plans.keys())
                    room_tabs = st.tabs(room_names)

                    unique_papers = day_students['PaperCode'].unique().tolist()
                    palette = ["#d62728", "#ff7f0e", "#2ca02c", "#1f77b4", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
                    paper_colors = {paper: palette[i % len(palette)] for i, paper in enumerate(unique_papers)}

                    for i, room_name in enumerate(plans.keys()):
                        with room_tabs[i]:
                            grid = plans[room_name]
                            room_total = sum(1 for row in grid for seat in row if seat)

                            st.subheader(f"Room: {room_name} | Students: {room_total} | Teacher: {assignments[room_name][0]}")

                            for row_idx, row in enumerate(grid):
                                cols = st.columns(len(row), gap="large")
                                for col_idx, seat in enumerate(row):
                                    with cols[col_idx]:
                                        if seat:
                                            sub_color = paper_colors.get(seat['paper'], "#000000")
                                            is_highlight = search_roll and str(seat['id']).lower() == search_roll.lower()
                                            if is_highlight:
                                                found_flag = True
                                                found_room = room_name

                                            border = "4px solid #00FFAA" if is_highlight else f"2px solid {sub_color}"
                                            glow = "0px 0px 18px rgba(0,255,170,0.7)" if is_highlight else "0px 2px 6px rgba(0,0,0,0.05)"
                                            scale = "scale(1.06)" if is_highlight else "scale(1)"

                                            st.markdown(f"""
                                            <div class="seat-card" style="
                                                border: {border};
                                                box-shadow: {glow};
                                                transform: {scale};
                                            ">
                                                <div class="seat-pos">R{row_idx+1}C{col_idx+1}</div>
                                                <div class="seat-id" style="color:{sub_color}">{seat['id']}</div>
                                                <div class="seat-paper" style="background-color:{sub_color}22; color:{sub_color}">
                                                    {seat['paper']}
                                                </div>
                                            </div>
                                            """, unsafe_allow_html=True)
                                        else:
                                            st.markdown('<div class="empty-seat">EMPTY</div>', unsafe_allow_html=True)
                                            
                    st.markdown("---")
                    
                    if search_roll:
                        if found_flag:
                            result_placeholder.success(f"✅ Student '{search_roll}' found in Room: {found_room}")
                        else:
                            result_placeholder.warning(f"⚠️ Student '{search_roll}' not found")
                            
                    # PDF Report Creation
                    pdf_bytes = create_pdf(plans, assignments, selected_date, selected_time)

                    # Log download function
                    def log_pdf_dl():
                        db_helper.log_activity(
                            user['email'], 
                            "Download PDF", 
                            f"Downloaded seating plan for {selected_date} ({selected_time})."
                        )

                    st.download_button(
                        label="📥 Download Seating Plan PDF Report",
                        data=pdf_bytes,
                        file_name=f"Exam_Plan_{selected_date}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        on_click=log_pdf_dl
                    )
            else:
                st.error("Error: Uploaded student dataset lacks 'ExamDate' or 'ExamTime' columns.")


# =========================================================================
# APPLICATION ROUTING INTERFACE
# =========================================================================
# Admin Panel routing back option in sidebar
if st.session_state.current_page == 'admin' and st.session_state.user:
    if st.sidebar.button("📅 Seating Planner Panel", use_container_width=True):
        st.session_state.current_page = 'app'
        st.rerun()

# ROUTE DISPATCHER
if st.session_state.user is None:
    show_landing_page()
elif st.session_state.current_page == 'onboarding':
    show_onboarding_page()
elif st.session_state.current_page == 'admin':
    show_admin_page()
else:
    show_main_app()

st.markdown("<p style='text-align: center; color: gray; font-size: 0.8em; margin-top: 50px;'>© Copyright 2026 - Jalaj Gupta | OptiSeat System</p>", unsafe_allow_html=True)
