import uuid
import jwt
from flask import Flask, jsonify, make_response, request
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from flask_cors import CORS, cross_origin
import os
from dotenv import load_dotenv
from models import TestCases, Tickets, TestRuns,Users ,Base
from functools import wraps
from werkzeug.security import generate_password_hash,check_password_hash
import datetime

load_dotenv()
app = Flask(__name__)
cors = CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token=None
        s=Session()
        if 'x-access-token' in request.headers:
            token=request.headers['x-access-token']

        if not token:
            return jsonify({'message':'A valid token is missing'})
        try:
            data=jwt.decode(token,os.getenv('SECRET_KEY'),algorithms=['HS256'])
            current_user=s.query(Users).filter_by(publicId=data['publicId']).first()
            s.close()
        except:
            s.close()
            return jsonify({'message':'token is invalid'},401)
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/register',methods=['POST'])
def register():
    s=Session()
    data=request.get_json()
    username=data['username']
    password=data['password']
    confirm_password=data['confirm']
    if password != confirm_password:
        return make_response('Passwords do not match',400)
    if not username or not password:
        return make_response('Credentials cannot be empty!', 401)
    hashed_password=generate_password_hash(data['password'],method='sha256')
    new_user=Users(publicId=(uuid.uuid4()), username=data['username'],password=hashed_password,admin=0)
    s.add(new_user)
    s.commit()
    s.close()
    return data

@app.route('/login', methods=['POST'])
@cross_origin()
def login():
    s=Session()

    data=request.get_json()
    username=data['username']
    password=data['password']

    if not username or not password:
        s.close()
        return make_response('Could not verify', 401)

    user=s.query(Users).filter_by(username=username).first()
    s.close()

    if not user:
        return make_response('Username is incorrect', 401)

    if check_password_hash(user.password, password):
        token = jwt.encode({'publicId': user.publicId,'admin':user.admin, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=120)}, os.getenv('SECRET_KEY'))
        return jsonify({'token': token})

    return make_response('Bad password', 402)

@app.route('/testcases')
@token_required
@cross_origin()
def get_all_testcase(current_user):
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
@token_required
def get_testcase_by_id(testcase_id,current_user):
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
@token_required
@cross_origin()
def create_testcase(current_user):
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
@token_required
@cross_origin(methods=['DELETE'])
def delete_testcase(current_user):
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
@token_required
@cross_origin()
def create_testrun(current_user):
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
@token_required
@cross_origin()
def update_testrun(current_user):
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
@token_required
@cross_origin()
def get_testrun(current_user):
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
@token_required
def get_tickets_by_testcase(current_user,testcase_id):
    output=[]
    s=Session()
    #tickets=s.query(Tickets.version,Tickets.tcID,Tickets.ticketLink).join(TestCases).where(and_(Tickets.version==version_nr,TestCases.id==testcase_id))
    tickets=s.query(Tickets.tcID,Tickets.ticketLink,Tickets.ticketName,Tickets.resolved).join(TestCases).where(TestCases.id==testcase_id)
    for ticket in tickets:
        ticket_data={}
        #ticket_data['version']=ticket.version
        ticket_data['tcID']=ticket.tcID
        ticket_data['ticketLink']=ticket.ticketLink
        ticket_data['ticketName']=ticket.ticketName
        ticket_data['resolved']=ticket.resolved
        output.append(ticket_data)
    s.close()
    print(output)
    return output

@app.route('/tickets/<testcase_id>', methods=['POST'])
@token_required
def create_ticket(current_user,testcase_id):
    data=request.get_json()
    s=Session()
    testcase=s.query(TestCases.id).where(TestCases.id==testcase_id).first()
    if testcase is None:
        s.close()
        return make_response('Testcase with this ID does not exists', 409)
    
    if s.query(Tickets.tcID,Tickets.ticketLink).where(and_(Tickets.tcID==testcase_id,Tickets.ticketLink==data['ticketLink'])).first() is not None:
        s.close()
        return make_response('This ticket already exists', 409)
    
    new_ticket=Tickets(tcid=testcase_id,ticketname=data['ticketName'],ticketlink=data['ticketLink'],resolved=0)
    print('itt')
    s.add(new_ticket)
    s.commit()

    response=jsonify(data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    s.close()
    print(data)
    return data

@app.route('/tickets/<testcase_id>', methods=['PUT'])
@token_required
def update_ticket(current_user,testcase_id):
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
    app.run(debug=True,host='0.0.0.0')
