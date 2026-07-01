# OptiSeats - Exam Seater Pro

Exam Seater Pro (OptiSeats) is a Python and Streamlit-based web application that automates exam seating arrangements for colleges and universities.

Live demo

- Try the live app: https://optiseat.streamlit.app/

## Features

- Generate optimized seating plans for exams
- Handle multiple rooms and varying capacities
- Prevent seating conflicts (e.g., same subject nearby)
- Export seating plans to CSV or printable formats
- Easy-to-use Streamlit web UI

## Requirements

- Python 3.8+
- pip

A ready-to-use requirements.txt is included in the repository. Install dependencies with:

```bash
pip install -r requirements.txt
```

If you prefer a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.\.venv\Scripts\activate   # Windows
```

## Running the app

- Run locally:

```bash
streamlit run app.py
```

If your main Streamlit file is named differently (for example `main.py` or `seater.py`), replace `app.py` with the correct filename.

- Or open the live demo in your browser: https://optiseat.streamlit.app/

## Example input data

This repository includes a sample `data/` folder with example CSVs to help you get started:

- `data/students.csv` — sample student list (student_id, name, roll, subject)
- `data/rooms.csv` — sample room list (room_id, room_name, capacity)
- `data/exams.csv` — sample exam schedule (exam_id, subject, date, start_time, duration_minutes)

Replace these files with your real data (keeping the same column headers), or use the app UI to upload CSVs.

Data folder URL: https://github.com/Jalaj-01/OptiSeats/tree/main/data

## Configuration

- Adjust algorithm constraints inside the project modules as needed.
- If the app expects a different path or filenames, update the code or provide the CSVs through the UI.

## Tests

If tests exist, run them with pytest:

```bash
pytest
```

## Contributing

Contributions and issues are welcome. Please open an issue to discuss changes or submit a pull request.

## License

This project is licensed under the MIT License — see [LICENSE](https://github.com/Jalaj-01/OptiSeats/blob/main/LICENSE) for details.

## Contact

Created by Jalaj-01 (Jalaj Gupta). For questions or help, please open an issue on this repository.
