from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
import os
import dotenv

dotenv.load_dotenv()
db_host = os.environ.get('db_host')
db_user = os.environ.get('db_username')
db_password = os.environ.get('db_password')
db_name = os.environ.get('db_name')
db_port = os.environ.get('db_port')
db_url = f"mysql://{db_user}:{db_password}@{db_host}/{db_name}"

db_mode = os.environ.get("DB_MODE", "polling")
if db_mode == 'webhook':
    db_url = f"mysql://{db_user}:{db_password}@{db_host}/{db_name}"
    engine = create_engine(f"{db_url}", pool_recycle=60)
else:
    engine = create_engine('sqlite:///test.db', echo=False, connect_args={'check_same_thread': False})

# engine = create_engine(db_url)
# engine = create_engine('sqlite:///test.db', echo=False)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory=session_factory)
Base = declarative_base()
