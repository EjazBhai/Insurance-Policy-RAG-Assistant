"""Launch the evaluation dashboard locally with `streamlit run eval/dashboard.py`."""
from pathlib import Path
import runpy

space_app = Path(__file__).resolve().parent / "hf_space" / "app.py"
runpy.run_path(str(space_app), run_name="__main__")
