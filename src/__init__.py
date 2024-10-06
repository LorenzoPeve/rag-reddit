from dotenv import load_dotenv
import os

ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')

load_dotenv(f".env.{ENVIRONMENT}", override=True)