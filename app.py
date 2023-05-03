from flask import Flask, jsonify, make_response, request
from sqlalchemy import *
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from flask_cors import CORS, cross_origin
import os
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
cors = CORS(app)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'  # Az adatbázis URI-ja, itt SQLite-ot használunk

server = 'DESKTOP-A8LE02Q\SQLEXPRESS'
database = 'testruns'
trusted_connection = 'Yes'

# Az adatbázis kapcsolat beállítása Windows autentikációval
#app.config['SQLALCHEMY_DATABASE_URI'] = f'mssql:///?odbc_connect=DRIVER={{ODBC Driver 17 for SQL Server}};' \
  #                                      f'SERVER={server};' \
   #                                     f'DATABASE={database};' \
    #                                    f'Trusted_Connection={trusted_connection};'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

Base = declarative_base()
Session = sessionmaker(bind=engine)


# TestCases model
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



Base.metadata.create_all(engine)


# Alkalmazás útválasztók
@app.route('/testcases')
@cross_origin()
def get_all_testcase():
    s = Session()
    testcases = s.query(TestCases).order_by(TestCases.id).all()
    output = []
    for testcase in testcases:
        testcase_data = {}
        testcase_data['id'] = testcase.id
        testcase_data['name'] = testcase.name
        output.append(testcase_data)
    s.close()
    return output


@app.route('/testcases/<testcase_id>')
@cross_origin()
def get_testcase_by_id(testcase_id):
    s = Session()
    testcase = s.query(TestCases).filter_by(id=testcase_id).first()
    if not testcase:
        s.close()
        return jsonify({'message': 'No testcases found!'})
    testcase_data = {}
    testcase_data['id'] = testcase.id
    testcase_data['name'] = testcase.name
    s.close()
    return jsonify(testcase_data)


@app.route('/testcases', methods=['POST'])
@cross_origin()
def create_testcase():
    data = request.get_json()
    s = Session()
    new_testcase = TestCases(name=data['name'])
    if s.query(TestCases).filter_by(name=data['name']).first() is not None:
        s.close()
        return make_response('Testcase already exists', 409)
    else:
        s.add(new_testcase)
        s.commit()
        response = jsonify(data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        s.close()
        return data


@app.route('/testcases', methods=['DELETE'])
@cross_origin(methods=['DELETE'])
def delete_testcase():
    data = request.get_json()
    s = Session()
    testcaseid = data['id']
    if s.query(TestCases).filter_by(id=testcaseid).first() is None:
        s.close()
        return make_response('Testcase not exists', 404)
    elif (s.query(TestRuns).filter_by(tcID=data['id']).first() is not None):
        s.close()
        return make_response('Testcases which have testrun cannot be deleted', 409)

    else:
        s.delete(s.query(TestCases).filter_by(id=testcaseid).first())
        s.commit()
        s.close()
        return data


@app.route('/testruns', methods=['POST'])
@cross_origin()
def create_testrun():
    s = Session()
    data = request.get_json()
    queriedId = s.query(TestCases.id).filter_by(name=data['name'])
    new_testrun = TestRuns(version=data['version'], tcid=queriedId, success=0)
    if s.query(TestCases).filter_by(name=data['name']).first() is None:
        return make_response('The selected testcase does not exist', 409)
    if s.query(TestRuns).filter_by(version=data['version']).filter_by(tcID=queriedId).first() is not None:
        return make_response('This testrun already contains this testcase', 409, )
    s.add(new_testrun)
    s.commit()
    response = jsonify(data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    s.close()
    return data


@app.route('/testruns', methods=['PUT'])
@cross_origin()
def update_testrun():
    data = request.get_json()
    s = Session()
    version = data['version']
    testcaseId = data['tcID']
    success = data['success']
    testrun = s.query(TestRuns).filter_by(version=version, tcID=testcaseId).first()
    if not testrun:
        return make_response('No Test Results found', 404)
    testrun.success = success
    s.commit()
    response = jsonify(data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    s.close()
    return data


@app.route('/testruns')
@cross_origin()
def get_testrun():
    output = []
    s = Session()
    testruns = s.query(TestRuns.version, TestCases.name, TestRuns.success, TestRuns.tcID).join(TestCases).order_by(
        TestRuns.version).all()
    if not testruns:
        s.close()
        return make_response('No TestResults found', 404)
    for testrun in testruns:
        testrun_data = {}
        testrun_data['name'] = testrun.name
        testrun_data['version'] = testrun.version
        testrun_data['sucess'] = testrun.success
        testrun_data['tcID'] = testrun.tcID
        output.append(testrun_data)
    s.close()
    return output

@app.route('/tickets/<testcase_id>')
def get_tickets_by_testcase(testcase_id):
    output=[]
    s=Session()
    #tickets=s.query(Tickets.version,Tickets.tcID,Tickets.ticketLink).join(TestCases).where(and_(Tickets.version==version_nr,TestCases.id==testcase_id))
    tickets=s.query(Tickets.tcID,Tickets.ticketLink,Tickets.ticketName,Tickets.resolved).join(TestCases).where(TestCases.id==testcase_id)
    if not tickets:
        s.close()
        return make_response('No Tickets for this testcase', 404)
    for ticket in tickets:
        ticket_data={}
        #ticket_data['version']=ticket.version
        ticket_data['tcID']=ticket.tcID
        ticket_data['ticketLink']=ticket.ticketLink
        ticket_data['ticketName']=ticket.ticketName
        ticket_data['resolved']=ticket.resolved
        output.append(ticket_data)
    s.close()
    return output

@app.route('/tickets/<testcase_id>', methods=['POST'])
def create_ticket(testcase_id):
    data=request.get_json()
    s=Session()
    testcase=s.query(TestCases.id).where(TestCases.id==data['tcID']).first()
    if testcase is None:
        s.close()
        return make_response('Testcase with this ID does not exists', 409)
    if s.query(Tickets.tcID,Tickets.ticketLink).where(and_(Tickets.tcID==data['tcID'],Tickets.ticketLink==data['ticketLink'])).first() is not None:
        s.close()
        return make_response('This ticket already exists', 409)
    new_ticket=Tickets(tcid=data['tcID'],ticketname=data['ticketName'],ticketlink=data['ticketLink'],resolved=0)
    s.add(new_ticket)
    s.commit()
    response=jsonify(data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    s.close()
    return data

@app.route('/tickets/<testcase_id>', methods=['PUT'])
def update_ticket(testcase_id):
    data=request.get_json()
    resolved=data['resolved']
    s=Session()
    ticket=s.query(Tickets).filter_by(ticketName=data['ticketName'],tcID=testcase_id).first()
    if not ticket:
        s.close()
        return make_response('No Ticket found', 404)
    ticket.resolved=resolved
    s.commit()
    response = jsonify(data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    s.close()
    return data

if __name__ == '__main__':
    # Adatbázis táblák létrehozása

    # Flask alkalmazás futtatása
    app.run(debug=True)
