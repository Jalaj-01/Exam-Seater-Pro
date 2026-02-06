import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
import math

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
    # return bytes(pdf.output())
    return pdf.output(dest="S").encode("latin-1")


def create_sample_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Exam Seater Pro", layout="wide")
st.title("🎓 Exam Seater Pro")

if 'plans' not in st.session_state:
    st.session_state.plans = None
    st.session_state.leftovers = 0

st.sidebar.markdown("## **Upload Data**") 

with st.sidebar.expander("🛠️ Need Test Files?"):
    s_df = pd.DataFrame({
        'RollNo': [f'STU{1000 + i}' for i in range(250)], 
        'PaperCode': (['CS101']*180 + ['MA202']*70), # Unbalanced subjects
        'ExamDate': (['2026-02-10']*250),
        'ExamTime': (['09:00 AM']*250)
    })
    r_df = pd.DataFrame({'RoomName': [f'ROOM-{i}' for i in range(1, 15)], 'Rows': [6]*14, 'Cols': [6]*14})
    f_df = pd.DataFrame({'Name': [f'Faculty-{i}' for i in range(1, 10)], 'DutiesDone': [0]*9})
    st.download_button("Download Students.xlsx", create_sample_excel(s_df), "students.xlsx")
    st.download_button("Download Rooms.xlsx", create_sample_excel(r_df), "rooms.xlsx")
    st.download_button("Download Faculty.xlsx", create_sample_excel(f_df), "faculty.xlsx")

file_students = st.sidebar.file_uploader("Upload Student List (Excel)", type=['xlsx'])
file_rooms = st.sidebar.file_uploader("Upload Room Details (Excel)", type=['xlsx'])
file_faculty = st.sidebar.file_uploader("Upload Faculty List (Excel)", type=['xlsx'])

if not (file_students and file_rooms and file_faculty):
    st.markdown(":green[**Ready to help! Please upload the Excel files in the sidebar to generate the arrangement.**]")
    st.markdown("### **Required Excel Formats:**")
    st.markdown("""
    *   **Students:** Columns: `RollNo` , `PaperCode`, `ExamDate`, `ExamTime`
    *   **Rooms:** Columns: `RoomName` , `Rows` , `Cols`
    *   **Faculty:** Columns: `Name` , `DutiesDone`
    """)
else:
    df_st = pd.read_excel(file_students)
    df_rm = pd.read_excel(file_rooms)
    df_fa = pd.read_excel(file_faculty)

    if 'ExamDate' in df_st.columns and 'ExamTime' in df_st.columns:
        dates = sorted(df_st['ExamDate'].unique().astype(str))
        col_d, col_t = st.columns(2)
        selected_date = col_d.selectbox("📅 Select Exam Date", dates)
        times = sorted(df_st[df_st['ExamDate'].astype(str) == selected_date]['ExamTime'].unique().astype(str))
        selected_time = col_t.selectbox("🕒 Select Exam Time/Shift", times)
        
        day_students = df_st[(df_st['ExamDate'].astype(str) == selected_date) & (df_st['ExamTime'].astype(str) == selected_time)]
        student_count = len(day_students)
        
        # --- NEW ACCURATE ESTIMATION LOGIC ---
        paper_counts = day_students['PaperCode'].value_counts()
        max_s = paper_counts.max()
        other_s = student_count - max_s
        
        # HEURISTIC: Dominant subject forces (Total - 2*Other) gaps
        # If max_s > other_s, we need gaps to separate the dominant subject
        # Required seats = Students + Required Gaps
        required_physical_seats = max(student_count, (2 * max_s) - 1)
        
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
            c3.error(f"⚠️ Gap Shortage: {required_physical_seats - total_capacity} extra seats needed for spacing")
        else:
            c3.success(f"✅ Safe Spacing: {total_capacity - required_physical_seats} surplus seats")

        if st.button("🚀 Generate Arrangement"):
            st.session_state.plans, st.session_state.leftovers = allocate_logic(day_students.copy(), df_rm)
            st.rerun()

        if st.session_state.plans:
            plans = st.session_state.plans
            leftovers = st.session_state.leftovers
            assignments = {}
            temp_fa = df_fa.copy()
            for room_name, grid in plans.items():
                temp_fa = temp_fa.sort_values(by='DutiesDone')
                chosen_teacher = temp_fa.iloc[0]['Name']
                temp_fa.at[temp_fa.index[0], 'DutiesDone'] += 1
                assignments[room_name] = [chosen_teacher]

            if leftovers > 0:
                st.warning(f"⚠️ Warning: {leftovers} students unseated. Spacing rules required {required_physical_seats} chairs, but rooms only provide {total_capacity}.")
            
            st.divider()
            st.header(f"🪑 Room Visualizations")
            room_tabs = st.tabs(list(plans.keys()))
            unique_papers = day_students['PaperCode'].unique().tolist()
            palette = ["#d62728", "#ff7f0e", "#2ca02c", "#1f77b4", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
            paper_colors = {paper: palette[i % len(palette)] for i, paper in enumerate(unique_papers)}

            for i, room_name in enumerate(plans.keys()):
                with room_tabs[i]:
                    grid = plans[room_name]
                    room_total = sum(1 for row in grid for seat in row if seat)
                    st.subheader(f"Room: {room_name} | Students: {room_total} | Teacher: {assignments[room_name][0]}")
                    for row_idx, row in enumerate(grid):
                        cols = st.columns(len(row))
                        for col_idx, seat in enumerate(row):
                            with cols[col_idx]:
                                if seat:
                                    sub_color = paper_colors.get(seat['paper'], "#000000")
                                    st.markdown(f"""<div style="border: 2px solid #eee; border-radius: 8px; padding: 5px; text-align: center; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); min-height: 90px;"><div style="font-size: 0.7em; color: #999; margin-bottom: 5px;">R{row_idx+1}C{col_idx+1}</div><div style="font-weight: bold; color: {sub_color}; font-size: 0.9em; overflow-wrap: break-word;">{seat['id']}</div><div style="font-size: 0.8em; font-weight: bold; background-color: {sub_color}22; color: {sub_color}; padding: 2px 5px; border-radius: 3px; display: inline-block; margin-top: 5px;">{seat['paper']}</div></div>""", unsafe_allow_html=True)
                                else:
                                    st.markdown("""<div style="border: 1px dashed #ddd; border-radius: 8px; padding: 5px; text-align: center; color: #eee; min-height: 90px; display: flex; align-items: center; justify-content: center; font-size: 0.7em;">EMPTY</div>""", unsafe_allow_html=True)

            pdf_bytes = create_pdf(plans, assignments, selected_date, selected_time)
            st.download_button(label="📥 Download PDF Report", data=pdf_bytes, file_name=f"Exam_Plan_{selected_date}.pdf", mime="application/pdf", use_container_width=True)
    else:
        st.error("Error: Missing columns.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray; font-size: 0.8em;'>© Copyright 2026 - Jalaj Gupta | Automated Seating System</p>", unsafe_allow_html=True)