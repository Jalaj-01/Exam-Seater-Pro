# 🎓 Exam Seater Pro

Exam Seater Pro is a Python and Streamlit-based web application that automates the process of exam seating arrangement for colleges and universities. It helps allocate students across multiple rooms while ensuring subject-wise spacing rules to maintain fairness and prevent adjacent seating of students from the same paper.

The platform supports Excel uploads for student, room, and faculty data, generates interactive room-wise seating visualizations, and provides downloadable and professional PDF reports including seating indexes and attendance sheets.

---

## 🚀 Features

- ✅ Automated student seat allocation with spacing constraints  
- 🏫 Multi-room seating support (rows × columns layout)  
- 👨‍🏫 Automatic invigilator assignment with fair duty tracking  
- 📊 Upload student, room, and faculty details via Excel files  
- 🎨 Interactive seating grid visualization  
- 📄 Downloadable PDF seating plan and attendance sheets  
- 📥 Sample Excel templates available for testing  

---

## 🛠 Tech Stack

- **Python**
- **Streamlit** (Web Interface)
- **Pandas** (Data Handling)
- **FPDF** (PDF Report Generation)
- **OpenPyXL / XlsxWriter** (Excel Support)

---

## 📂 Required Excel Formats

### Students File
Columns:
- `RollNo`
- `PaperCode`
- `ExamDate`
- `ExamTime`

### Rooms File
Columns:
- `RoomName`
- `Rows`
- `Cols`

### Faculty File
Columns:
- `Name`
- `DutiesDone`

---

## ▶️ How to Run the Project

### 1. Install Dependencies

```bash
pip install streamlit pandas openpyxl xlsxwriter fpdf


