import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import db 

if __name__ == "__main__":
    db.init_schema()