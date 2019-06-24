from flask_restful import Resource
from werkzeug.exceptions import BadRequest
from flask import request,jsonify,g
from datetime import datetime
from sqlalchemy import exists,and_
from sqlalchemy.orm.exc import NoResultFound
from common.json_schema import Schedule_Schema
from common.utils import headers,is_logged_in,has_admin_privileges
from common.utils import bad_request,unauthorized,forbidden,not_found,internal_server_error,unprocessable_entity,conflict

class Schedule_RUD(Resource):
    """
    For GET UPDATE and DELETE for specific hardware id
    """
    def get(self,schedule_id):
        """
        GET the hardware details based on specific hardware_id
        """
        #using get instead of filter and it is marginally faster than filter
        #check for multiple entries need to be done at POST and not during GET or PUT or DELETE
        try:
            schedule_item = g.session.query(g.Base.classes.schedules).get(schedule_id)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        if schedule_item:
            ret = Schedule_Schema().dump(schedule_item).data
            return (ret,200,headers)
        else:
            return (not_found,404,headers)

    def put(self,schedule_id):
        """
        Update the hardware. Required data: title, description, time, location
        """
        #check if data from request is serializable
        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        #data validation
        if Schedule_Schema().validate(data):
            return (unprocessable_entity,422,headers)

        #check if user has admin privileges
        user_status,user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        if user_status in ["director","organizer"]:
            try:
                schedule_item = g.session.query(g.Base.classes.schedules).get(schedule_id)
                if schedule_item:
                    schedule_item.title = data["title"]
                    schedule_item.description = data["description"]
                    schedule_item.time = data["time"]
                    schedule_item.location = data["location"]
                    schedule_item.updated_at = datetime.now()
                    ret = Schedule_Schema().dump(schedule_item).data
                    return (ret,200,headers)
                else:
                    return (not_found,404,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error,500,headers)
        else:
            return (forbidden,403,headers)

    def delete(self,schedule_id):
        """
        DELETE request to delete hardware based on specific hardware_id. This is new from the old api.
        """
        user_status,user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        if user_status in ["director","organizer"]:
            try:
                #this makes sure that at least one hardware matches hardware id
                schedule_item_to_delete = g.session.query(g.Base.classes.schedules).get(schedule_id)
                if schedule_item_to_delete:
                    g.session.query(g.Base.classes.schedules).filter(g.Base.classes.schedules.id == schedule_id).delete()
                    return ("",204,headers)
                else:
                    return (not_found,404,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error,500,headers)
        else:
            return (forbidden,403,headers)

class Schedule_CR(Resource):
    """
    To create new hardware using POST and read all hardware items
    """
    def post(self):
        """
        Create new hardware. Required data: item,lender, quantity
        """
        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        #data validation
        if Schedule_Schema().validate(data):
            return (unprocessable_entity,422,headers)

        #check if user has admin privileges
        user_status,user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        try:
            exist_check = g.session.query(exists().where(and_(g.Base.classes.schedules.title == data["title"],g.Base.classes.schedules.location == data["location"]))).scalar()
            if exist_check:
                return (conflict,409,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        if user_status in ["director","organizer"]:
            Schedule = g.Base.classes.schedules
            try:
                new_schedule_item = Schedule(
                                                title = data["title"],
                                                description = data["description"],
                                                time = data["time"],
                                                location = data["location"],
                                                updated_at = datetime.now(),
                                                created_at = datetime.now()
                                            )
                g.session.add(new_schedule_item)
                g.session.commit()
                ret = g.session.query(g.Base.classes.schedules).filter(g.Base.classes.schedules.title == data["title"]).one()
                return (Schedule_Schema().dump(ret).data,201 ,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error,500,headers)
        else:
            return(forbidden,403,headers)

    def get(self):
        """
        GET all the announcements at a time.
        """
        try:
            all_schedule_items = g.session.query(g.Base.classes.schedules).all()
            ret = Schedule_Schema(many = True).dump(all_schedule_items).data
            return (ret,200,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)
