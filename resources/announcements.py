from flask_restful import Resource
from werkzeug.exceptions import BadRequest
from flask import request,jsonify,g, current_app
from datetime import datetime
from sqlalchemy import exists,and_
from sqlalchemy.orm.exc import NoResultFound
from common.json_schema import Announcement_Schema
from common.utils import headers,is_logged_in,has_admin_privileges
from common.utils import bad_request,unauthorized,forbidden,not_found,internal_server_error,unprocessable_entity,conflict

class Announcements_RUD(Resource):
    """
    For GET PUT and DELETE for specific announcement
    """
    def get(self,announcement_id):
        #using get instead of query and it is marginally faster than filter
        #check for multiple entries need to be done at POST and not during GET or PUT or DELETE
        try:
            announcement = g.session.query(g.Base.classes.announcements).get(announcement_id)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        if announcement:
            ret = Announcement_Schema().dump(announcement).data
            return (ret,200,headers)
        else:
            return (not_found,404,headers)

    def put(self,announcement_id):
        """
        updating announcements. Required things - title, description, pinned
        """
        #check if data from request is serializable
        try:
            data = request.get_json(force=True)
        except BadRequest:
            bad_request['error_list']['error']='Bad request received. Please contact hello@spartahack.com for further assistance.'
            current_app.logger.warning('Bad JSON request found. Request:',str(request))
            return (bad_request,400,headers)

        #data validation
        if Announcement_Schema().validate(data):
            return (unprocessable_entity,422,headers)

        #check if user has admin privileges
        user_status,user = has_admin_privileges()
        if user_status == "no_auth_token":
            bad_request['error_list']['error']='Bad request received. Please contact hello@spartahack.com for further assistance.'
            current_app.logger.warning('Access tried without privileges.',str(user.id))
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            
            return (unauthorized,401,headers)

        if user_status in ["director","organizer"]:
            try:
                announcement = g.session.query(g.Base.classes.announcements).get(announcement_id)
                if announcement:
                    announcement.title = data["title"]
                    announcement.description = data["description"]
                    announcement.pinned = data["pinned"]
                    announcement.updated_at = datetime.now()
                    ret = Announcement_Schema().dump(announcement).data
                    return (ret,200,headers)
                else:
                    return (not_found,404,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error,500,headers)
        else:
            return (forbidden,403,headers)

    def delete(self,announcement_id):
        """
        For DELETE request for specific id
        """
        user_status,user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        if user_status in ["director","organizer"]:
            try:
                #this makes sure that at least one announcement matches announcement_id
                announcement_to_delete = g.session.query(g.Base.classes.announcements).get(announcement_id)
                if announcement_to_delete:
                    g.session.query(g.Base.classes.announcements).filter(g.Base.classes.announcements.id == announcement_id).delete()
                    return ("",204,headers)
                else:
                    return (not_found,404,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error, 500, headers)
        else:
            return (forbidden,403,headers)
class Announcements_CR(Resource):
    """
    For GET PUT and DELETE for specific announcement
    """
    def post(self):
        """
        For POST request. Checks for bad JSON from request, checks if data types in request JSON are correct, Checks user auth status and if he's logged in.
        """
        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        #data validation
        if Announcement_Schema().validate(data):
            return (unprocessable_entity,422,headers)

        #check if user has admin privileges
        user_status,user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        #checking if announcement with same title and description already exists. To manage duplicate entries
        try:
            exist_check = g.session.query(exists().where(and_(g.Base.classes.announcements.title == data["title"],g.Base.classes.announcements.description == data["description"]))).scalar()
            if exist_check:
                return (conflict,409,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        if user_status in ["director","organizer"]:
            Announcements = g.Base.classes.announcements
            try:
                new_announcement = Announcements(
                                                    title = data["title"],
                                                    description = data["description"],
                                                    pinned = data["pinned"],
                                                    updated_at = datetime.now(),
                                                    created_at = datetime.now()
                                                )
                g.session.add(new_announcement)
                g.session.commit()
                ret = g.session.query(g.Base.classes.announcements).filter(g.Base.classes.announcements.description == data["description"]).one()
                return (Announcement_Schema().dump(ret).data,201 ,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error,500,headers)
        else:
            return(forbidden,403,headers)

    def get(self):
        """
        Getting all the announcements by hitting /announcements endpoint without any specific id
        """
        try:
            all_announcements = g.session.query(g.Base.classes.announcements).all()
            ret = Announcement_Schema(many = True).dump(all_announcements).data
            return (ret,200,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)
