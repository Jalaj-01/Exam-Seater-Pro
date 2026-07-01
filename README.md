# OptiSeats - Exam Seater Pro

Exam Seater Pro (OptiSeats) is a Python and Streamlit-based web application that automates exam seating arrangements for colleges and universities.

## Features

- Generate optimized seating plans for exams
- Handle multiple rooms and varying capacities
- Prevent seating conflicts (e.g., same subject nearby)
- Export seating plans to CSV or printable formats
- Easy-to-use Streamlit web UI

## Requirements

- Python 3.8+
- pip

Recommended to create and use a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.\.venv\Scripts\activate   # Windows
```

Install dependencies:

```bash
pip install -r requirements.txt
```

If the repository does not include a requirements.txt, you can at minimum install Streamlit:

```bash
pip install streamlit
```

## Running the app

From the project root, run:

```bash
streamlit run app.py
```

If your main Streamlit file is named differently (for example `main.py` or `seater.py`), replace `app.py` with the correct filename.

Open the provided local URL in a browser (usually http://localhost:8501).

## Configuration

- Provide input data (students, subjects, rooms, capacities) via the app UI or place CSV files in a documented data/ folder.
- Adjust algorithm or constraints inside the project modules as needed.

## Tests

If tests exist, run them with pytest:

```bash
pytest
```

## Contributing

Contributions and issues are welcome. Please open an issue to discuss changes or submit a pull request.

## License

Add a LICENSE file to state the project's license. If you don't have one yet, consider using an open-source license such as MIT.

## Contact

Created by Jalaj-01. For questions or help, please open an issue on this repository.
