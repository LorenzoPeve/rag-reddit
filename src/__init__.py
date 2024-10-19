from dotenv import load_dotenv
import os

load_dotenv(override=True)
load_dotenv(f".env.{os.getenv('ENVIRONMENT')}", override=True)