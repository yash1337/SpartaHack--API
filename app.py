#importing extensions
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask_cors import CORS
from sqlalchemy.orm import Session
from flask import Flask, jsonify, make_response, request, g
from flask.cli import AppGroup
import click

#importing API stuff
from common.utils import unauthorized,headers,not_found
from config import DevelopmentConfig, ProdConfig
from resources.faqs import Faqs_RUD, Faqs_CR
from resources.announcements import Announcements_RUD, Announcements_CR
from resources.hardware import Hardware_RUD, Hardware_CR
from resources.sponsors import Sponsor_RD, Sponsor_CR
from resources.schedule import Schedule_RUD, Schedule_CR
from resources.applications import Applications_RU, Applications_CR
from resources.users import Users_RD, Users_CRU, Users_Change_Role, Users_Reset_Password_Token, Users_Reset_Password, Users_Change_Password
from resources.sessions import Sessions_C,Sessions_D
from resources.rsvps import RSVP_CR,RSVP_RD
from resources.checkin import Checkin_CR


#importing python stuff
from logging.config import dictConfig
import logging
import os,sys


def register_extensions(app,api):
    """
    Register Flask extensions.
    """
    #initializing CORS object
    CORS(app,origins=[eval(os.getenv("CORS_ADDRESSES"))])

    #initializing api object
    api.init_app(app)

def register_before_requests(app,Base,engine):
    """
    Register before_request functions.
    """
    def create_session():
        """
        Before processing any request. Create a session by checking out a connection from the connection pool.
        Also set global variables to be accessed for the life time of the request
        """
        g.session = Session(engine)
        g.Base = Base

    app.before_request(create_session)

def register_teardown_requests(app):
    """
    Register after_request functions.
    """
    def close_session(err):
        """
        After all the processing is done. Close the session to return the connection object back to the connection pool.
        """
        g.session.close()

    app.teardown_request(close_session)

def register_hello_world_route(app):
    def helloworld():
        """
        For flask app test and general info about the API.
        Will also be used to check if the api is live or not on the slack hook
        """
        metadata = {
                    "Organization":"SpartaHack",
                    "Backend Developer":"Yash",
                    "Frontend Developers":"Harrison, Jessica, Jarek",
                    "Contact":"hello@spartahack.com",
                    "Version": os.getenv("VERSION")
                    }

        app.logger.info('this is an INFO message')
        app.logger.warning('this is a WARNING message')
        app.logger.error('this is an ERROR messag')
        app.logger.info("Root url accessed",stack_info=True)
        app.logger.error('this is another error with breadcrumbs CRITICAL message')

        return (jsonify(metadata),200,headers)
    app.add_url_rule('/','/',helloworld)

def register_resources(api):
    """
    Register resources on api object
    """
    #adding resources. Just flask-restful things :)
    api.add_resource(Faqs_RUD,"/faqs/<int:faq_id>")
    api.add_resource(Faqs_CR,"/faqs")
    api.add_resource(Announcements_RUD,"/announcements/<int:announcement_id>")
    api.add_resource(Announcements_CR,"/announcements")
    api.add_resource(Hardware_RUD,"/hardware/<int:hardware_id>")
    api.add_resource(Hardware_CR,"/hardware")
    api.add_resource(Sponsor_RD,"/sponsors/<int:sponsor_id>")
    api.add_resource(Sponsor_CR,"/sponsors")
    api.add_resource(Schedule_RUD,"/schedule/<int:schedule_id>")
    api.add_resource(Schedule_CR,"/schedule")
    api.add_resource(Applications_RU,"/applications/<int:application_id>")
    api.add_resource(Applications_CR,"/applications")
    api.add_resource(Users_RD,"/users/<int:user_id>")
    api.add_resource(Users_CRU,"/users")
    api.add_resource(Users_Change_Role,"/users/change_user_role")
    api.add_resource(Users_Reset_Password_Token,"/users/request_password_token")
    api.add_resource(Users_Reset_Password,"/users/reset_password")
    api.add_resource(Users_Change_Password,"/users/change_password")
    api.add_resource(Sessions_D,"/sessions/<user_token>")
    api.add_resource(Sessions_C,"/sessions")
    api.add_resource(RSVP_RD,"/rsvps/<int:user_id>")
    api.add_resource(RSVP_CR,"/rsvps")
    api.add_resource(Checkin_CR,"/checkin")

    #might only need this for email sending so that email sending does not clog up the resources
    #task_queue=Celery("SpartaHack_API_2019",broker=app.config["CELERY_BROKER_URL"])

def create_app(config):
    """
    Flask application factory method
    Sets up extentions and default routes
    """
    #setting up sentry-sdk for logging exceptions and logs
    sentry_sdk.init(
                        dsn=os.environ['SENTRY_DSN'],
                        integrations=[FlaskIntegration()],
                        environment=os.getenv("FLASK_ENV"),
                        release=f"spartahackapi@{os.getenv('VERSION')}"
                    )
    app = Flask(os.getenv("PROJECT"))
    app.config.from_object(eval(config)) #loading config data into flask app from config object.

    from extensions import api, Base, engine

    register_before_requests(app,Base,engine)
    register_teardown_requests(app)
    register_resources(api)
    register_hello_world_route(app)
    register_extensions(app,api)

    return app
