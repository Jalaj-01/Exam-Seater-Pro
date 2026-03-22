import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
import math
import json
import pdfplumber 

st.markdown("""
<style>

/* ===== GLOBAL RESET ===== */
.block-container {
    padding-top: 0rem !important;
    margin-top: 0rem !important;
}

/* Hide header completely */
header {visibility: hidden; height: 0px;}

/* ===== SIDEBAR PERFECT ALIGNMENT ===== */

/* Remove all sidebar padding */
section[data-testid="stSidebar"] {
    padding: 0rem !important;
}

/* Control sidebar container */
section[data-testid="stSidebar"] > div {
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;  /* 🔥 THIS FIXES TOP/BOTTOM BALANCE */
    padding: 0.5rem 0.5rem !important;
    overflow: auto;
}
/* Smooth scrollbar */
section[data-testid="stSidebar"]::-webkit-scrollbar {
    width: 6px;
}
section[data-testid="stSidebar"]::-webkit-scrollbar-thumb {
    background: #ccc;
    border-radius: 10px;
}
/* Remove internal top gap */
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
    margin-top: 0rem !important;
    padding-top: 0rem !important;
}

/* Remove hidden spacer div (IMPORTANT FIX) */
section[data-testid="stSidebar"] div:first-child {
    margin-top: 0rem !important;
    padding-top: 0rem !important;
}

/* ===== FILE UPLOADER ===== */
[data-testid="stFileUploader"] {
    margin-top: 8px;
    margin-bottom: 12px;
}

/* ===== FONT ===== */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
.seat-card {
    margin: 6px;
    border: 2px solid;
    border-radius: 12px;
    padding: 8px;
    text-align: center;
    background: white;
    min-height: 95px;
    transition: all 0.25s ease;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0px 2px 6px rgba(0,0,0,0.05);
}
.seat-card:hover {
    transform: scale(1.05);   /* reduced from 1.08 */
    z-index: 10;
    position: relative;
    box-shadow: 0px 8px 20px rgba(0,0,0,0.2);
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
    color: #ddd;
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
        elif file_extension in ['csv', 'txt']: # Added 'txt' support here
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

# --- CORE LOGIC ---
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

# --- PDF GENERATOR ---
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
                    master_list.append({'RollNo': str(seat['id']), 'Paper': seat['paper'], 'Room': room_name, 'Seat': f"R{r_idx+1}C{c_idx+1}"})
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
        pdf.cell(0, 8, f"Invigilator: {', '.join(assignments[room_name])}", 0, 1)
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

# --- STREAMLIT UI ---
# --- STREAMLIT UI ---
st.set_page_config(page_title="OptiSeat", layout="wide")

st.markdown("""
<style>
.header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 20px;
    border-bottom: 1px solid #eee;
    margin-bottom: 20px;
}

.logo {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1f2937;
}

.tagline {
    font-size: 0.9rem;
    color: #6b7280;
}
</style>

<div class="header">
    <div class="logo">🎓 OptiSeat</div>
    <div class="tagline">Smart Exam Seating System</div>
</div>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'plans' not in st.session_state:
    st.session_state.plans = None
    st.session_state.leftovers = 0

# --- SIDEBAR ---
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

    st.markdown("### **Required Columns:**")
    st.markdown("""
    *   **Students:** `RollNo` , `PaperCode`, `ExamDate`, `ExamTime`
    *   **Rooms:** `RoomName` , `Rows` , `Cols`
    *   **Faculty:** `Name` , `DutiesDone`
    """)

else:
    df_st = load_data(file_students)
    df_rm = load_data(file_rooms)
    df_fa = load_data(file_faculty)

    # ===== ✅ FIXED DASHBOARD (MOVED HERE) =====
    total_students = len(df_st)
    total_rooms = len(df_rm)
    total_subjects = df_st['PaperCode'].nunique()
    total_faculty = len(df_fa)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("🎓 Students", total_students)
    col2.metric("🏫 Rooms", total_rooms)
    col3.metric("📚 Subjects", total_subjects)
    col4.metric("👨‍🏫 Faculty", total_faculty)

    st.markdown("---")

    # --- EXISTING LOGIC CONTINUES ---
    if df_st is not None and 'ExamDate' in df_st.columns and 'ExamTime' in df_st.columns:

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
        max_s = paper_counts.max()
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

        if st.button("🚀 Generate Arrangement"):
            st.session_state.plans, st.session_state.leftovers = allocate_logic(day_students.copy(), df_rm)
            st.rerun()

        if st.session_state.plans:
            plans = st.session_state.plans
            assignments = {}

            temp_fa = df_fa.copy()
            temp_fa['DutiesDone'] = pd.to_numeric(temp_fa['DutiesDone'])

            for room_name, grid in plans.items():
                temp_fa = temp_fa.sort_values(by='DutiesDone')
                chosen_teacher = temp_fa.iloc[0]['Name']
                temp_fa.at[temp_fa.index[0], 'DutiesDone'] += 1
                assignments[room_name] = [chosen_teacher]
            
            search_roll = st.text_input("🔍 Search Student by Roll Number")
           
            # INIT (ONLY ONCE)
            found_flag = False
            found_room = None
            result_placeholder = st.empty()
            st.markdown("---")
            st.header("🪑 Room Visualizations")
            

            room_names = list(plans.keys())
            default_index = 0
            if found_room and found_room in room_names:
                default_index = room_names.index(found_room)
            
            room_tabs = st.tabs(room_names)

            if found_room:
                st.session_state["active_tab"] = default_index

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
            # ===== SHOW RESULT ONLY ONCE (AFTER LOOP) =====
            if search_roll:
                if found_flag:
                    result_placeholder.success(f"✅ Student '{search_roll}' found in Room: {found_room}")
                else:
                    result_placeholder.warning(f"⚠️ Student '{search_roll}' not found")
            pdf_bytes = create_pdf(plans, assignments, selected_date, selected_time)

            st.download_button(
                label="📥 Download PDF Report",
                data=pdf_bytes,
                file_name=f"Exam_Plan_{selected_date}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    else:
        st.error("Error: Column missing or format not recognized.")

st.markdown("---")

st.markdown("<p style='text-align: center; color: gray; font-size: 0.8em;'>© Copyright 2026 - Jalaj Gupta</p>", unsafe_allow_html=True)
