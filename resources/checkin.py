from flask_restful import Resource
from werkzeug.exceptions import BadRequest
from flask import request,jsonify,g
from flask import current_app as app
from marshmallow import validate,ValidationError
from sqlalchemy import exists,and_
from sqlalchemy.orm.exc import NoResultFound
from jinja2 import Template
from common.json_schema import User_Schema
from common.utils import headers,is_logged_in,has_admin_privileges,encrypt_pass,waste_time,verify_pass,send_email
from common.utils import bad_request,unauthorized,forbidden,not_found,internal_server_error,unprocessable_entity,conflict,gone
from datetime import datetime,timedelta,date


class Checkin_CR(Resource):
    """
    To create new user using POST and read all users. PUT only allowed by
    Required data: email, first_name, last_name
    """
    def post(self):
        """
        Check users in. Required data: user_id
        """
        def is_minor(application):
            today = date.today()
            age = today.year - application.birth_year - ((today.month, today.day) < (application.birth_month, application.birth_day))
            return age < 18

        Users = g.Base.classes.users
        Applications = g.Base.classes.applications
        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)
        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        if data.get("id","error") == "error":
            unprocessable_entity["error_list"]["id"] = "User id missing!"
            return (unprocessable_entity,422,headers)


        # getting the user. Assuming the user exists. Case of user not existing is checked below
        try:
            user = g.session.query(g.Base.classes.users).get(data["id"])

        except Exception as err:
            app.logger.info(f'SQLAlchemy error {err}',stack_info=True)
            app.logger.error(f'Error getting the user for id {data["id"]}')
            return (internal_server_error,500,headers)

        try:
            user_app = g.session.query(Applications).filter(Applications.user_id == data["id"]).one()
        except Exception as err:
            app.logger.info(f'SQLAlchemy error {err}',stack_info=True)
            app.logger.error(f'Error getting the user app for id {data["id"]}')
            return (internal_server_error,500,headers)

        #* only organizers and directors can check people in
        if user and user_app:
            try:
                if user_status in ["director","organizer","volunteer"]:
                    if user.checked_in:
                        if is_minor(user_app):
                            return (f"{user.first_name} {user.last_name} is already checked in!! and is also a minor!",200,headers)
                        else:
                            return (f"{user.first_name} {user.last_name} is already checked in!!",200,headers)
                    else:
                        if is_minor(user_app):
                            user.checked_in = True
                            g.session.commit()
                            return (f"{user.first_name} {user.last_name} is checked in!! and is also a minor!",201,headers)
                        user.checked_in = True
                        g.session.commit()
                        return (f"{user.first_name} {user.last_name} is checked in!!",201,headers)
                else:
                    forbidden["error_list"]={"Authorization error":"You do not privileges to access this resource. Contact one of the organizers if you think require access."}
                    return (forbidden,403,headers)
            except Exception as err:
                app.logger.info("Something happened that shouldn't",stack_info=True)
                app.logger.info(f'Specific error {err}')
                app.logger.error(f'Check in error for user {user}')
                return (internal_server_error, 500, headers)
        else:
            return (not_found,404,headers)
