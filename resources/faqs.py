from flask_restful import Resource
from werkzeug.exceptions import BadRequest
from flask import request,jsonify,g
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy import exists,and_
from common.json_schema import Faq_Schema
from marshmallow.exceptions import ValidationError
from datetime import datetime
from common.utils import headers,is_logged_in,has_admin_privileges
from common.utils import bad_request,unauthorized,forbidden,not_found,internal_server_error,unprocessable_entity,conflict

class Faqs_RUD(Resource):
    """
    For GET PUT and DELETE for specific faq
    get http headers using request.headers.get("header_name")
    """
    def get(self,faq_id):
        #using get instead of query and it is marginally faster than filter
        #check for multiple entries need to be done at POST and not during GET or PUT or DELETE
        try:
            faq_object = g.session.query(g.Base.classes.faqs).get(faq_id)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        if faq_object:
            ret = Faq_Schema().dump(faq_object).data
            return (ret,200,headers)
        else:
            return (not_found,404,headers)


    def put(self,faq_id):
        """
        For updating the faq based on specific faq_id.
        Required data: question, answer, display, priority, placement
        """
        #check if data from request is serializable
        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        #data validation
        if Faq_Schema().validate(data):
            return (unprocessable_entity,422,headers)

        #check if user has admin privileges
        user_status,user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        if user_status in ["director","organizer"]:
            try:
                faq_object = g.session.query(g.Base.classes.faqs).get(faq_id)
                if faq_object:
                    faq_object.question = data["question"]
                    faq_object.answer = data["answer"]
                    faq_object.display = data["display"]
                    faq_object.priority = data["priority"]
                    faq_object.placement = data["placement"]
                    faq_object.user_id = user.id
                    faq_object.updated_at = datetime.now()
                    ret = Faq_Schema().dump(faq_object).data
                    return (ret,200,headers)
                else:
                    return (not_found,404,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error,500,headers)
        else:
            return (forbidden,403,headers)



    def delete(self,faq_id):
        """
        To delete the FAQ based on specific faq_id
        """
        #check if user has admin privileges
        user_status,user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        if user_status in ["director","organizer"]:
            try:
                faq_to_delete = g.session.query(g.Base.classes.faqs).get(faq_id)
                if faq_to_delete:
                    #this makes sure that at least one faq matches faq_id
                    g.session.query(g.Base.classes.faqs).filter(g.Base.classes.faqs.id == faq_id).delete()
                    return ("",204,headers)
                else:
                    return (not_found,404,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error,500,headers)
        else:
            return (forbidden,403,headers)

class Faqs_CR(Resource):
    """
    For adding a new faq through POST and getting all the FAQS
    """
    def post(self):
        #request validation
        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        #data validation
        if Faq_Schema().validate(data):
            return (unprocessable_entity,422,headers)

        #check if user has admin privileges
        user_status,user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        #checking if faq with same questions and answer already exists. To manage duplicate entries. Check out SQLAlchemy documentation to learn how exists work
        try:
            exist_check = g.session.query(exists().where(and_(g.Base.classes.faqs.question == data["question"],g.Base.classes.faqs.answer == data["answer"]))).scalar()
            if exist_check:
                return (conflict,409,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        if user_status in ["director","organizer"]:
            try:
                Faqs = g.Base.classes.faqs
                new_faq = Faqs(
                                question = data["question"],
                                answer = data["answer"],
                                user_id = user.id,
                                created_at = datetime.now(),
                                updated_at = datetime.now(),
                                display = data["display"],
                                priority = data["priority"],
                                placement = data["placement"]
                              )
                g.session.add(new_faq)
                g.session.commit()
                #first() or one() shouldn't matter because we already checked if an faq without same question and answer exits
                new_faq = g.session.query(g.Base.classes.faqs).filter(g.Base.classes.faqs.question == data["question"]).one()
                return (Faq_Schema().dump(new_faq).data,201,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error,500,headers)
        else:
            return(forbidden,403,headers)

    def get(self):
        """
        For returning all the faqs.
        """
        try:
            all_faqs=g.session.query(g.Base.classes.faqs).all()
            ret=[]
            for faq in all_faqs:
                ret.append(Faq_Schema().dump(faq).data)
            return (ret,200,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)
