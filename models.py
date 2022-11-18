from dbhelper import Base, Session
from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Text, func, Date
from sqlalchemy.orm import relationship, backref
import datetime
# import logging


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False, unique=True)
    tg_username = Column(String(255), nullable=True, unique=True)
    name = Column(String(255), nullable=False)
    email_id = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now())
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.now())
    timezones = relationship("Timezone", back_populates='users', lazy='dynamic')
    wakesleeps = relationship("Wakesleep", back_populates='users', lazy='dynamic')
    foods = relationship("Food", back_populates='users', lazy='dynamic')
    gyms = relationship("Gym", back_populates='users', lazy='dynamic')
    yogas = relationship("Yoga", back_populates='users', lazy='dynamic')
    pranayams = relationship("Pranayam", back_populates='users', lazy='dynamic')
    thoughts = relationship("Thoughts", back_populates='users', lazy='dynamic')
    tasks = relationship("Taskcompleted", back_populates='users', lazy='dynamic')
    rundowns = relationship("Rundown", back_populates='users', lazy='dynamic')
    # records = relationship("Record", back_populates='users', lazy='dynamic')
    # bookmarks = relationship("Bookmark", back_populates='users', lazy='dynamic')


    @classmethod
    def get_user(cls, session, id):
        return session.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_user_by_chatid(cls, session, chat_id):
        return session.query(cls).filter(cls.chat_id == chat_id).first()

    @classmethod
    def get_all_users(cls, session):
        return session.query(cls).all()

    def update_email(self, session, email):
        self.email_id = email
        session.add(self)
        try:
            session.commit()
            return self
        except:
            session.rollback()
            return None

    def __repr__(self):
        return f"<User: id {self.id}, chat_id {self.chat_id}, name {self.name}, email_id {self.email_id} created_at {self.created_at}, updated_at {self.updated_at}>"


class Timezone(Base):
    __tablename__ = 'timezones'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    timezone_name = Column(String(255), nullable=False)
    timezone_offset = Column(String(255), nullable=False)
    effective_from = Column(Date, nullable=False, default=datetime.datetime.now())
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now())
    users = relationship('User')

    @classmethod
    def get_timezone_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).first()

    def __repr__(self):
        return f"Timezone :- id - {self.id}, user_id - {self.user_id}, effective_from - {self.effective_from}, timezone_name - {self.timezone_name}, created_at - {self.created_at} "


#uid, comment
class Wakesleep(Base):
    __tablename__ = 'wakesleeps'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    sleeptime = Column(DateTime, nullable=False)
    wakeuptime = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now())
    users = relationship('User')

    @classmethod
    def get_all_wakesleeps_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).all()

    @classmethod
    def get_latest_wakesleep_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).first()

    @classmethod
    def get_wakesleep_by_date_and_userid(cls, session, date, userid):
        pass
        # return session.query(cls).filter(cls.id == userid).first()

    def __repr__(self):
        return f"Wakesleep :- id - {self.id}, user_id - {self.user_id}, sleeptime - {self.sleeptime}, wakeuptime - {self.wakeuptime}, notes - {self.notes}, created_at - {self.created_at}"


class Food(Base):
    __tablename__ = 'foods'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    food_item = Column(Text, nullable = False)
    food_label = Column(Text, nullable = False)
    food_time = Column(DateTime, nullable=False)
    food_photos = Column(Text, nullable=True)
    food_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now())
    users = relationship('User')

    @classmethod
    def get_all_food_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).all()

    @classmethod
    def get_latest_food_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).first()

    @classmethod
    def get_food_by_date_and_userid(cls, session, date, userid):
        pass
        # return session.query(cls).filter(cls.id == userid).first()

    def __repr__(self):
        return f"Food :- id - {self.id}, user_id - {self.user_id}, food_time - {self.food_time}, food items - {', '.join(self.food_item)}, food photos - {self.food_photos},food_notes - {self.food_notes}, created_at - {self.created_at}"

class Gym(Base):
    __tablename__ = 'gyms'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    gym_datetime = Column(DateTime, nullable=False)
    gym_type = Column(String(255), nullable=False)
    total_set = Column(Integer, nullable=False)
    repetition = Column(String(255), nullable=False)
    weight = Column(String(255), nullable=False)
    gym_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now())
    users = relationship('User')

    @classmethod
    def get_all_gym_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).all()

    @classmethod
    def get_latest_gym_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).first()

    @classmethod
    def get_gym_by_date_and_userid(cls, session, date, userid):
        pass
        # return session.query(cls).filter(cls.id == userid).first()

    def __repr__(self):
        return f"Gym :- id - {self.id}, user_id - {self.user_id}, gym_datetime - {self.gym_datetime}, gym_type - {self.gym_type}, total_set - {self.total_set}, repetition - {self.repetition}, weight - {self.weight}, gym_notes - {self.gym_notes}, created_at - {self.created_at}"

class Yoga(Base):
    __tablename__ = 'yogas'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    yoga_type = Column(String(255), nullable=False)
    yoga_datetime = Column(DateTime, nullable=False)
    repetition = Column(Integer, nullable=False)
    yoga_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now())
    users = relationship('User')

    @classmethod
    def get_all_yoga_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).all()

    @classmethod
    def get_latest_yoga_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).first()

    @classmethod
    def get_yoga_by_date_and_userid(cls, session, date, userid):
        pass
        # return session.query(cls).filter(cls.id == userid).first()

    def __repr__(self):
        return f"Yoga :- id - {self.id}, user_id - {self.user_id}, yoga_type - {self.yoga_type}, yoga_datetime - {self.yoga_datetime}, repetition - {self.repetition}, yoga_notes - {self.yoga_notes}, created_at - {self.created_at}"

class Pranayam(Base):
    __tablename__ = 'pranayams'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    pranayam_type = Column(String(255), nullable=False)
    pranayam_datetime = Column(DateTime, nullable=False)
    repetition = Column(Integer, nullable=False)
    pranayam_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now())
    users = relationship('User')

    @classmethod
    def get_all_pranayam_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).all()

    @classmethod
    def get_latest_pranayam_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).first()

    @classmethod
    def get_pranayam_by_date_and_userid(cls, session, date, userid):
        pass
        # return session.query(cls).filter(cls.id == userid).first()

    def __repr__(self):
        return f"Pranayama :- id - {self.id}, user_id - {self.user_id}, pranayam_type - {self.pranayam_type}, pranayam_datetime - {self.pranayam_datetime}, repetition - {self.repetition}, pranayam_notes - {self.pranayam_notes}, created_at - {self.created_at}"

class Thoughts(Base):
    __tablename__ = 'thoughts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    thoughts = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now())
    users = relationship('User')

    @classmethod
    def get_all_thoughts_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).all()

    @classmethod
    def get_latest_thoughts_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).first()

    @classmethod
    def get_thoughts_by_date_and_userid(cls, session, date, userid):
        pass
        # return session.query(cls).filter(cls.id == userid).first()

    def __repr__(self):
        return f"Thoughts :- id - {self.id}, user_id - {self.user_id}, thoughts - {self.thoughts}, created_at - {self.created_at}"


class Taskcompleted(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    tasks = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.now())
    users = relationship('User')

    @classmethod
    def get_all_thoughts_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).all()

    @classmethod
    def get_latest_thoughts_by_userid(cls, session, userid):
        return session.query(cls).filter(cls.id == userid).first()

    @classmethod
    def get_thoughts_by_date_and_userid(cls, session, date, userid):
        pass
        # return session.query(cls).filter(cls.id == userid).first()

    def __repr__(self):
        return f"Completed Tasks :- id - {self.id}, user_id - {self.user_id}, tasks - {self.tasks}, created_at - {self.created_at}"

