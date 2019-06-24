from flask_restful import Resource
from werkzeug.exceptions import BadRequest
from flask import request,jsonify,g
from datetime import datetime
from sqlalchemy import exists,and_
from jinja2 import Template
from sqlalchemy.orm.exc import NoResultFound
from common.json_schema import Application_Schema
from common.utils import headers,is_logged_in,has_admin_privileges,waste_time, send_email
from common.utils import bad_request,unauthorized,forbidden,not_found,internal_server_error,unprocessable_entity,conflict

class Applications_RU(Resource):
    """
    For GET PUT for specific application
    get http headers using request.headers.get("header_name")
    """
    def get(self,application_id):
        """
        GET the application details based on specific application_id
        """
        #using get instead of filter and it is marginally faster than filter
        #check for multiple entries need to be done at POST and not during GET or PUT or DELETE
        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        # getting the application. Assuming the application exists. Case of application  not existing is checked below
        try:
            application = g.session.query(g.Base.classes.applications).get(application_id)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        # *Only allow directors, organizers and the user making the request to access his own user id to access this resource
        # *Compare user_id rather than complete user objects because it's faster
        if application:
            if user_status in ["director","organizer"] or calling_user.id == application.user_id:
                ret = Application_Schema().dump(application).data
                return (ret,200,headers)
            else:
                return (forbidden,403,headers)
        else:
            return (not_found,404,headers)

    def put(self,application_id):
        """
        Update the application. Required data: application_id
        birth_day
        birth_month
        birth_year
        education
        university
        other_university
        travel_origin
        graduation_season
        graduation_year
        major
        hackathons
        github
        linkedin
        website
        devpost
        other_link
        statement
        race
        gender
        outside_north_america
        reimbursement
        phone
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
        validation = Application_Schema().validate(data)
        if validation:
            unprocessable_entity["error_list"] = validation
            return (unprocessable_entity,422,headers)

        #* get application for the calling user
        try:
            application = g.session.query(g.Base.classes.applications).get(application_id)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        # *Only allow user making the request to access their own application id to access this resource
        # *The original data to be provided in the request. Just updated value setting will be implemented in PATCH which would be in API 2.0
        if application:
                try:
                    if user_status in ["director","organizer"] or calling_user.id == application.user_id:
                        application.birth_day = data['birth_day']
                        application.birth_month = data['birth_month']
                        application.birth_year = data['birth_year']
                        application.education = data['education']
                        application.university = data['university']
                        application.other_university = data['other_university']
                        application.travel_origin = data['travel_origin']
                        application.graduation_season = data['graduation_season']
                        application.graduation_year = data['graduation_year']
                        application.major = list(set(data['major']))
                        application.hackathons = data['hackathons']
                        application.github = data['github']
                        application.linkedin = data['linkedin']
                        application.website = data['website']
                        application.devpost = data['devpost']
                        application.other_link = data['other_link']
                        application.statement = data['statement']
                        application.updated_at = datetime.now()
                        application.race = list(set(data['race']))
                        application.gender = data['gender']
                        application.outside_north_america = data['outside_north_america']
                        application.status = data['status']
                        application.reimbursement = data['reimbursement']
                        application.phone = data['phone']

                        ret = Application_Schema().dump(application).data
                        return (ret,200,headers)
                    else:
                        return (forbidden,403,headers)
                except Exception as err:
                    print(type(err))
                    print(err)
                    return (internal_server_error,500,headers)
        else:
            return (not_found,404,headers)

    def delete(self,application_id):
        """
        Delete the application. Required data: application_id
        """
        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        # getting the application. Assuming the application exists. Case of application  not existing is checked below
        try:
            application = g.session.query(g.Base.classes.applications).get(application_id)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        # *Only allow directors, organizers and the user making the request to access his own user id to access this resource
        # *Compare user_id rather than complete user objects because it's faster
        if application:
            try:
                if user_status in ["director","organizer"] or calling_user.id == application.user_id:
                    g.session.delete(g.session.query(g.Base.classes.applications).get(application_id))
                    return ("",204,headers)
                else:
                    return (forbidden,403,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error, 500, headers)
        else:
            return (not_found,404,headers)

class Applications_CR(Resource):
    """
    To create new application using POST and read all applications
    """
    def post(self):
        """
        Create new application. Required data:
        birth_day
        birth_month
        birth_year
        education
        university
        other_university
        travel_origin
        graduation_season
        graduation_year
        major
        hackathons
        github
        linkedin
        website
        devpost
        other_link
        statement
        race
        gender
        outside_north_america
        reimbursement
        phone
        """
        try:
            data = request.get_json(force=True)
        except BadRequest:
            return (bad_request,400,headers)

        # *request data validation. Check for empty fields will be done by frontend
        validation = Application_Schema().validate(data)
        if validation:
            unprocessable_entity["error_list"]=validation
            return (unprocessable_entity,422,headers)

        Applications = g.Base.classes.applications
        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        # check if application already submitted
        try:
            exist_check = g.session.query(exists().where(Applications.user_id == calling_user.id)).scalar()
            if exist_check:
                waste_time()
                return (conflict,409,headers)
        except Exception as err:
            print(type(err))
            print(err)
            return (internal_server_error,500,headers)

        try:
            new_application = Applications(
                                            user_id = calling_user.id,
                                            birth_day = data['birth_day'],
                                            birth_month = data['birth_month'],
                                            birth_year = data['birth_year'],
                                            education = data['education'],
                                            university = data['university'],
                                            other_university = data['other_university'],
                                            travel_origin = data['travel_origin'],
                                            graduation_season = data['graduation_season'],
                                            graduation_year = data['graduation_year'],
                                            major = list(set(data['major'])),
                                            hackathons = data['hackathons'],
                                            github = data['github'],
                                            linkedin = data['linkedin'],
                                            website = data['website'],
                                            devpost = data['devpost'],
                                            other_link = data['other_link'],
                                            statement = data['statement'],
                                            created_at = datetime.now(),
                                            updated_at = datetime.now(),
                                            race = list(set(data['race'])),
                                            gender = data['gender'],
                                            outside_north_america = data['outside_north_america'],
                                            status = "Applied",
                                            reimbursement = data['reimbursement'],
                                            phone = data['phone']
                                          )
            g.session.add(new_application)
            g.session.commit()
            ret = g.session.query(Applications).filter(Applications.user_id == calling_user.id).one()
            ret = Application_Schema().dump(ret).data
        except Exception as err:
                print(type(err))
                print(err)
                internal_server_error["error_list"]["error"] = "Error in application submission. Please try again."
                return (internal_server_error,500,headers)

        # error handling for mail send
        try:
            f = open("common/application_submitted.html",'r')
            body = Template(f.read())
            f.close()
            body = body.render(first_name = calling_user.first_name)
            send_email(subject = "Application submission confirmation!",recipient = calling_user.email, body = body)
            return (ret,201,headers)
        except Exception as err:
            print(type(err))
            print(err)
            internal_server_error["error_list"]["error"] = "Application successfully submitted. Error in confirmation email sending."
            return (internal_server_error,500,headers)


    def get(self):
        """
        GET all the applications at a time.
        """
        user_status,calling_user = has_admin_privileges()
        if user_status == "no_auth_token":
            return (bad_request,400,headers)

        if user_status == "not_logged_in":
            return (unauthorized,401,headers)

        if user_status in ["director","organizer"]:
            try:
                all_applications = g.session.query(g.Base.classes.applications).all()
                ret = Application_Schema(many = True).dump(all_applications).data
                return (ret,200,headers)
            except Exception as err:
                print(type(err))
                print(err)
                return (internal_server_error,500,headers)
        else:
            return (forbidden,403,headers)
