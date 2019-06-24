from flask_restful import Resource
from werkzeug.exceptions import BadRequest
from flask import request,jsonify,g
from datetime import datetime
from sqlalchemy import exists,and_
from jinja2 import Template
from sqlalchemy.orm.exc import NoResultFound
from common.json_schema import RSVP_Schema
from common.utils import headers,is_logged_in,has_admin_privileges,waste_time,send_email
from common.utils import bad_request,unauthorized,forbidden,not_found,internal_server_error,unprocessable_entity,conflict

class RSVP_RD(Resource):
    """
    For GET DELETE for specific rsvp
    get http headers using request.headers.get("header_name")
    """
    def get(self,user_id):
        """
        GET the rsvp details based on specific user_id
        """
        #using get instead of filter and it is marginally faster than filter
        #check for multiple entries need to be done at POST and not during GET or PUT or DELETE
        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        # getting the rsvp. Assuming the rsvp exists. Case of application  not existing is checked below
        try:
            rsvp = g.session.query(g.Base.classes.rsvps).filter(g.Base.classes.rsvps.user_id == user_id).first()
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        if rsvp:
            if user_status in ["director","organizer"] or calling_user.id == rsvp.user_id:
                ret = RSVP_Schema().dump(rsvp).data
                return (ret,200,headers)
            else:
                return (forbidden,403,headers)
        else:
            return (not_found,404,headers)

    def delete(self,user_id):
        """
        DELETE the rsvp details based on specific user_id
        This will probably not be used by the user
        """
        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        # getting the user. Assuming the user exists. Case of user not existing is checked below
        try:
            rsvp = g.session.query(g.Base.classes.rsvps).filter(g.Base.classes.rsvps.user_id == user_id).first()
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        if rsvp:
            try:
                if user_status in ["director","organizer"] or calling_user.id == rsvp.user_id:
                    g.session.delete(g.session.query(g.Base.classes.rsvps).get(rsvp.id))
                    return ("",204,headers)
                else:
                    return (forbidden,403,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error, 500, headers)
        else:
            return (not_found,404,headers)



class RSVP_CR(Resource):
    """
    For POST and GET for all rsvps
    get http headers using request.headers.get("header_name")
    """
    def post(self):
        """
        Create new rsvp Required data:
        attending
        dietary_restrictions
        other_dietary_restrictions
        resume
        shirt_size
        carpool_sharing
        jobs
        """

        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        # *request data validation. Check for empty fields will be done by frontend
        validation = RSVP_Schema().validate(data)
        if validation:
            unprocessable_entity["error_list"]=validation
            return (unprocessable_entity,422,headers)

        Rsvps = g.Base.classes.rsvps
        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        # check if rsvp already submitted
        try:
            exist_check = g.session.query(exists().where(Rsvps.user_id == calling_user.id)).scalar()
            if exist_check:
                return (conflict,409,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        try:
            new_rsvp = Rsvps(
                                user_id = calling_user.id,
                                attending = data["attending"],
                                dietary_restrictions = list(set(data["dietary_restrictions"])),
                                other_dietary_restrictions = data["other_dietary_restrictions"],
                                resume = data["resume"],
                                shirt_size = data["shirt_size"],
                                carpool_sharing = data["carpool_sharing"],
                                jobs = data["jobs"],
                                created_at = datetime.now(),
                                updated_at = datetime.now()
                            )
            g.session.add(new_rsvp)
            g.session.commit()
            ret = g.session.query(Rsvps).filter(Rsvps.user_id == calling_user.id).one()
            ret = RSVP_Schema().dump(ret).data
            return (ret,201,headers)
        except Exception as err:
                print(type(err))
                print(err)
                internal_server_error["error_list"]["error"] = "Error in RSVP submission. Please try again."
                return (internal_server_error,500,headers)

    def get(self):
        """
        GET all the rsvps at a time.
        """
        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        if user_status in ["director","organizer"]:
            try:
                all_rsvps = g.session.query(g.Base.classes.rsvps).all()
                ret = RSVP_Schema(many = True).dump(all_rsvps).data
                return (ret,200,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error,500,headers)
        else:
            return (forbidden,403,headers)
