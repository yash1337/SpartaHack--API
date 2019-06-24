from flask_restful import Resource
from werkzeug.exceptions import BadRequest
from flask import request,jsonify,g
from flask import current_app as app
from marshmallow import validate,ValidationError
from sqlalchemy import exists,and_
from sqlalchemy.orm.exc import NoResultFound
from jinja2 import Template
from common.json_schema import User_Schema,User_Input_Schema,User_Change_Role_Schema,User_Reset_Password_Schema
from common.utils import headers,is_logged_in,has_admin_privileges,encrypt_pass,waste_time,verify_pass,send_email
from common.utils import bad_request,unauthorized,forbidden,not_found,internal_server_error,unprocessable_entity,conflict,gone
from datetime import datetime,timedelta
import string
import random
import secrets

class Users_RD(Resource):
    """
    For GET and DELETE for specific user_id
    Director, Organizer should be able to get any user details and delete any user but not update
    """
    def get(self,user_id):
        """
        GET the user details based on specific user_id
        We are considering user and application separate entities. Previously, a user submitted the application details at the time of user account creation.
        Now, the user creates an account and then logs in to submit the application.
        Compared to old API we are not returning the application and rsvp details with the user details, rather we are returning the application_id and rsvp_id to help the front-end make GET request on application and rsvp endpoint in a separate requests.
        """
        #using get instead of query and it is marginally faster than filter
        #check for multiple entries need to be done at POST and not during GET or PUT or DELETE
        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        # getting the user. Assuming the user exists. Case of user not existing is checked below
        try:
            user = g.session.query(g.Base.classes.users).get(user_id)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        # *Only allow directors, organizers and the user making the request to access his own user id to access this resource
        # *Compare user_id rather than complete user objects because it's faster
        if user:
            if user_status in ["director","organizer"] or calling_user.id == user.id:
                ret = User_Schema().dump(user).data
                # *<class_name>_collection is way by which SQLAlchemy stores relationships.
                # *The collection object contains one related object in one-to-one relationship and more than one object in one-to-many relationships
                # *set application_id if application object is found in the applications_collection i.e. if the user has submitted the application
                # *This is different than old API in the sense that a user does not necessarily have a application at the time of account creation. User has the option of submitting the application later on.
                ret["application_id"] = user.applications_collection[0].id if user.applications_collection else None
                # *set rsvp_id if rsvp object is found in the rsvps_collection i.e. if the user has rsvped
                ret["rsvp_id"] = user.rsvps_collection[0].id if user.rsvps_collection else None
                return (ret,200,headers)
            else:
                forbidden["error_list"]={"Authorization error":"You do not privileges to access this resource. Contact one of the organizers if you think require access."}
                return(forbidden,403,headers)
        else:
            return (not_found,404,headers)

    def delete(self,user_id):
        """
        DELETE user request. Only Directors, Organizers and user calling the request
        """
        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        # getting the user. Assuming the user exists. Case of user not existing is checked below
        try:
            user = g.session.query(g.Base.classes.users).get(user_id)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        # *Only Directors, Organizers and user calling the request
        if user:
            try:
                if user_status in ["director","organizer"] or calling_user.id == user.id:
                    if user.rsvps_collection:
                        g.session.delete(g.session.query(g.Base.classes.rsvps).get(user.rsvps_collection[0].id))
                    if user.applications_collection:
                        g.session.delete(g.session.query(g.Base.classes.applications).get(user.applications_collection[0].id))
                    g.session.delete(g.session.query(g.Base.classes.users).get(user_id))
                else:
                    forbidden["error_list"]={"Authorization error":"You do not privileges to access this resource. Contact one of the organizers if you think require access."}
                    return (forbidden,403,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error, 500, headers)
        else:
            return (not_found,404,headers)

        # error handling for mail send
        try:
            f = open("common/account_creation.html",'r')
            body = Template(f.read())
            f.close()
            body = body.render(first_name = user.first_name)
            send_email(subject = "Account creation confirmation!",recipient = user.email, body = "Account deleted!")
            return ("",204,headers)
        except Exception as err:
            print(type(err))
            print(err)
            internal_server_error["error_list"]["error"] = "Account successfully created. Error in confirmation email sending."
            return (internal_server_error,500,headers)


class Users_CRU(Resource):
    """
    To create new user using POST and read all users. PUT only allowed by
    Required data: email, first_name, last_name
    """
    def put(self):
        """
        Update user. Required data: email, first_name, last_name, password, confirmation_password
        PUT is allowed only by users on their own objects.
        """
        #check if data from request is serializable
        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)
        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        # *request data validation. Check for empty fields will be done by frontend
        validation = User_Input_Schema().validate(data)
        if validation:
            unprocessable_entity["error_list"] = validation["_schema"][0]
            return (unprocessable_entity,422,headers)

        # *Only allow user making the request to access their own user id to access this resource
        # *The original email, first_name and last_name to be provided in the request. Just updated value setting will be implemented in PATCH which would be in API 2.0
        try:
            calling_user.email = data["email"]
            calling_user.first_name = data["first_name"]
            calling_user.last_name = data["last_name"]

            return (User_Schema().dump(calling_user).data,200,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

    def post(self):
        """
        Create new user. Required data: email,password,confirmation_password,first_name,last_name
        """
        Users = g.Base.classes.users
        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        # *request data validation. Check for empty fields will be done by frontend
        validation = User_Input_Schema().validate(data)
        if validation:
            unprocessable_entity["error_list"]=validation["_schema"][0]
            return (unprocessable_entity,422,headers)

        # check if user already signed up
        try:
            exist_check = g.session.query(exists().where(Users.email == data["email"])).scalar()
            if exist_check:
                waste_time()
                return (conflict,409,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        try:
            new_user = Users(
                                email = data["email"],
                                encrypted_password = encrypt_pass(data["password"]),
                                sign_in_count = 0,
                                checked_in = False,
                                role = 64,
                                auth_token = secrets.token_urlsafe(25),
                                first_name = data["first_name"],
                                last_name = data["last_name"],
                                confirmation_token = secrets.token_urlsafe(15),
                                confirmation_sent_at = datetime.now(),
                                updated_at = datetime.now(),
                                created_at = datetime.now()
                            )
            g.session.add(new_user)
            g.session.commit()
            ret = g.session.query(Users).filter(Users.email == data["email"]).one()
        except Exception as err:
            print(type(err))
            print(err)
            internal_server_error["error_list"]["error"] = "Error in account creation. Please try again."
            return (internal_server_error,500,headers)

        # error handling for mail send
        try:
            f = open("common/account_creation.html",'r')
            body = Template(f.read())
            f.close()
            body = body.render(first_name = data["first_name"])
            send_email(subject = "Account creation confirmation!",recipient = data["email"], body = body)
            return (User_Schema().dump(ret).data,201,headers)
        except Exception as err:
            print(type(err))
            print(err)
            internal_server_error["error_list"]["error"] = "Account successfully created. Error in confirmation email sending."
            return (internal_server_error,500,headers)

    def get(self):
        """
        GET all the users at a time.
        Application_id and rsvp_id is not gonna be returned when GET is called on all the users.
        Because getting the application_id and rsvp_id makes db calls and making calls for application_id and rsvp_id on hundreds of users is costly.
        """
        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        # *Only allow directors, organizers to make GET on all users (I don't really see the need for this tbh!)maybe for accepting applications
        if user_status in ["director","organizer","volunteer"]:
            try:
                all_users = g.session.query(g.Base.classes.users).all()
                ret = User_Schema(many = True).dump(all_users).data
                return (ret,200,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error,500,headers)
        else:
            forbidden["error_list"]={"Authorization error":"You do not privileges to access this resource. Contact one of the organizers if you think require access."}
            return(forbidden,403,headers)

class Users_Change_Role(Resource):
    """
    Update roles for users. Required data: email,role, role_change_password
    """
    def post(self):
        """
        Only method needed
        """
        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        # *request data validation
        validation = User_Change_Role_Schema().validate(data)
        if validation:
            unprocessable_entity["error_list"] = validation["_schema"][0]
            return (unprocessable_entity,422,headers)

        # getting the user. Assuming the user exists. Case of user not existing is checked below
        try:
            user = g.session.query(g.Base.classes.users).filter(g.Base.classes.users.email == data["email"]).one()
        except NoResultFound:
            # *If no user with that email is found with that token then you send 422 error
            not_found["error_list"]["email"] = "No user found with that email"
            return (not_found,404,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        # *Only directors have the ability to change user roles
        try:
            if user_status in ["director"] and data["role_change_password"] == app.config["ROLE_CHANGE_PASS_DEV"]:
                user.role = 2**(["director","judge","mentor","sponsor","organizer","volunteer","hacker"].index(data["role"]))
                return (User_Schema().dump(user).data,200,headers)
            else:
                forbidden["error_list"]={"Authorization error":"You do not privileges to access this resource. Contact one of the organizers if you think require access."}
                return (forbidden,403,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

class Users_Reset_Password_Token(Resource):
    """
    Create password reset token
    """
    def post(self):
        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        try:
            validator = validate.Email()
            validator(data["email"])
        except ValidationError:
            unprocessable_entity["error_list"]["email"] = "Not an valid email!"
            return (unprocessable_entity,422,headers)

        # getting the user. Assuming the user exists. Case of user not existing is checked below
        try:
            user = g.session.query(g.Base.classes.users).filter(g.Base.classes.users.email == data["email"]).one()
        except NoResultFound:
            # *If no email is found with that address then you return 200 and send the email either way say
            # *Your confirmation message displayed on the web page would simply say “An email has been sent to (provided email address) with further instructions.”
            return ({"email":data["email"]},200,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        try:
            # *create reset password token and send email
            if user:
                user.reset_password_token = secrets.token_urlsafe(15)
                user.reset_password_sent_at = datetime.now(),
                user.auth_token = secrets.token_urlsafe(25)
            else:
                return (not_found,404,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        # error handling for mail send
        try:
            f = open("common/reset_password.html",'r')
            body = Template(f.read())
            f.close()
            body = body.render(reset_password_token = user.reset_password_token)
            send_email(subject = "SpartaHack Password Reset",recipient = data["email"], body = body)
            return ({"status":"Reset password token set at "+data["email"]},200,headers)
        except Exception as err:
            print(type(err))
            print(err)
            internal_server_error["error_list"]["error"] = "Password reset token created but error in sending email"
            return (internal_server_error,500,headers)

class Users_Reset_Password(Resource):
    """
    Reset password using reset password token
    """
    def post(self):
        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        # *request data validation. Check for empty fields will be done by frontend
        validation = User_Reset_Password_Schema().validate(data)
        if validation:
            unprocessable_entity["error_list"] = validation["_schema"][0]
        if not request.headers.get("X-WWW-RESET-PASSWORD-TOKEN",default=False):
            unprocessable_entity["error_list"]["reset_password_token"] = "Password reset token required"
        if unprocessable_entity["error_list"]:
            return (unprocessable_entity,422,headers)

        # getting the user for the specific reset password token. Assuming the user exists. Case of user not existing is checked below
        try:
            user = g.session.query(g.Base.classes.users).filter(g.Base.classes.users.reset_password_token == request.headers.get("X-WWW-RESET-PASSWORD-TOKEN")).one()
        except NoResultFound:
            # *If no user is found with that token then you send 422 error
            not_found["error_list"]["X-WWW-RESET-PASSWORD-TOKEN"] = "No user found with that password reset token"
            return (not_found,404,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        try:
            # *change password of user for given reset password token and token hasn't expired
            if user:
                if (datetime.now() - user.reset_password_sent_at).days < 2:
                    user.encrypted_password = encrypt_pass(data["password"])
                    user.updated_at = datetime.now()
                    return (User_Schema().dump(user).data,200,headers)
                else:
                    return (gone,410,headers)
            else:
                return (not_found,404,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

class Users_Change_Password(Resource):
    """
    Change user password through normal account login
    """
    def post(self):
        """
        Only method needed
        """
        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)
        try:
            data = request.get_json(force = True)
        except BadRequest:
            return (bad_request,400,headers)

        # *request data validation. Check for empty fields will be done by frontend
        validation = User_Reset_Password_Schema().validate(data)
        if validation:
            if not  data.get("current_password"):
                unprocessable_entity["error_list"]["current_password"] = "Current password is required"
            unprocessable_entity["error_list"] = validation["_schema"][0]
            return (unprocessable_entity,422,headers)

        # *change password of user through normal account login
        try:
            # *proceed only if user exists
            if calling_user:
                # *proceed only if current_password is correct
                if verify_pass(data["current_password"],calling_user.encrypted_password):
                    calling_user.encrypted_password = encrypt_pass(data["password"])
                    calling_user.updated_at = datetime.now()
                else:
                    forbidden["error_list"]["current_password"] = "Current password is not correct"
                    return (forbidden,403,headers)

                return (User_Schema().dump(calling_user).data,200,headers)
            else:
                return (not_found,404,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)
