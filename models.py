from sqlalchemy import *
from sqlalchemy.orm import declarative_base

Base = declarative_base()
class TestCases(Base):
    __tablename__ = 'testcases'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)

    def __init__(self, name):
        self.name = name

class TestRuns(Base):
    __tablename__ = 'testruns'
    id = Column(Integer, primary_key=True, nullable=False, unique=True)
    version = Column(Integer, nullable=False)
    tcID = Column(Integer, ForeignKey('testcases.id'), nullable=False)
    success = Column(Integer)

    def __init__(self, version, tcid, success):
        self.version = version
        self.tcID = tcid
        self.success = success


class Tickets(Base):
    __tablename__ = 'tickets'
    id = Column(Integer, primary_key=True, nullable=False, unique=True)
    #version = Column(Integer, nullable=False)
    tcID = Column(Integer, ForeignKey('testcases.id'), nullable=False)
    ticketName=Column(String(200),unique=True,nullable=False)
    ticketLink = Column(String(200))
    resolved=Column(Integer)

    def __init__(self, tcid, ticketlink,ticketname,resolved):
        #self.version = version
        self.tcID = tcid
        self.ticketLink = ticketlink
        self.ticketName=ticketname
        self.resolved=resolved

class Users(Base):
    __tablename__ = 'users'
    id=Column(Integer,primary_key=True,nullable=False,unique=True)
    publicId=Column(String(250),unique=True)
    username=Column(String(50),unique=True,nullable=False)
    password=Column(String(100),nullable=False)
    admin=Column(Integer)

    def __init__(self , publicId, username, password,admin):
        # self.version = version
        self.publicId = publicId
        self.username = username
        self.password = password
        self.admin = admin
