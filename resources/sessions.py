from flask_restful import Resource
from werkzeug.exceptions import BadRequest
from flask import request,jsonify,g
from datetime import datetime
from sqlalchemy import exists,and_
from sqlalchemy.orm.exc import NoResultFound
from common.json_schema import Sessions_Schema,User_Schema
from common.utils import headers,is_logged_in,has_admin_privileges,waste_time,verify_pass
from common.utils import bad_request,unauthorized,forbidden,not_found,internal_server_error,unprocessable_entity,conflict
import random
import secrets

class Sessions_D(Resource):
    """
    For DELETE for specific session
    get http headers using request.headers.get("header_name")
    """
    def delete(self,user_token):
        """
        Delete the session. Required data: user_token
        """
        # getting the user. Assuming the user exists. Case of user not existing is checked below
        try:
            user = g.session.query(g.Base.classes.users).filter(g.Base.classes.users.auth_token == user_token).one()
        except NoResultFound:
            # *If no user with that email is found with that token then you send 403 error
            forbidden["error_list"]["token"] = "User not logged in"
            return (forbidden,403,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)
        auth_token = secrets.token_urlsafe(25)
        user.auth_token = auth_token
        return ('',204,headers)

class Sessions_C(Resource):
    """
    To create new session using POST
    """
    def post(self):
        """
        for POST for session
        """
        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        # *request data validation. Check for empty fields will be done by frontend
        validation = Sessions_Schema().validate(data)
        if validation:
            unprocessable_entity["error_list"]=validation
            return (unprocessable_entity,422,headers)

        # getting the user. Assuming the user exists. Case of user not existing is checked below
        try:
            user = g.session.query(g.Base.classes.users).filter(g.Base.classes.users.email == data["email"]).one()
        except NoResultFound:
            # *If no user with that email is found with that token then you send 403 error
            forbidden["error_list"]["email"] = "No user found with that email and password combination"
            return (forbidden,403,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        auth_token = secrets.token_urlsafe(25)
        if verify_pass(data["password"],user.encrypted_password):
            user.auth_token = auth_token
            ret = User_Schema().dump(user).data
            # *This is different than old API in the sense that a user does not necessarily have a application at the time of account creation. User has the option of submitting the application later on.
            ret["application_id"] = user.applications_collection[0].id if user.applications_collection else None
            # *set rsvp_id if rsvp object is found in the rsvps_collection i.e. if the user has rsvped
            ret["rsvp_id"] = user.rsvps_collection[0].id if user.rsvps_collection else None
            return (ret,200,headers)
        else:
            forbidden["error_list"]["email"] = "No user found with that email and password combination"
            return (forbidden,403,headers)