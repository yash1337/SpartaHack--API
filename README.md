# SpartaHack-API-2019

[![Build Status](https://travis-ci.org/SpartaHack/SpartaHack_API_2019.svg?branch=master)](https://travis-ci.org/SpartaHack/SpartaHack_API_2019)
[![CodeFactor](https://www.codefactor.io/repository/github/spartahack/spartahack_api_2019/badge/develop)](https://www.codefactor.io/repository/github/spartahack/spartahack_api_2019/overview/develop)

The New SpartaHack API

Steps to run a local copy of SpartaHackAPI

1. Install virtualenv and virtualenvwrapper to the global python installation (source [Virtualenv and Virtualenvwrapper](http://docs.python-guide.org/en/latest/dev/virtualenvs/))  
    ```bash
    pip3 install virtualenv
    ```  
    ```bash
    pip3 install virtualenvwrapper
    ```  
   And add the following three lines to your shell startup file (.zshrc, .bashrc, .profile, etc.)  
   Python location might change depending on what OS you are using(on MacOS it was stored in `/usr/local/bin/python3`), for Ubuntu 16.04:  

    ```bash
    export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
    export WORKON_HOME=~/.virtualenvs
    source /usr/local/bin/virtualenvwrapper.sh
    ```
2. Clone the API and cd into it  
3. Create a virtualenv using `mkvirtualenv [VIRTUALENV_NAME]` using the virtualenvwrapper
    * Side Note: This will create the environment at the location you selected(the location put in your .zshrc)  
4. Switch the python interpreter to the virtualenv using `workon [VIRTUALENV_NAME]`  
5. Install the dependencies using `pip install -r requirements.txt`  
6. Install RabbitMQ server using `sudo apt install rabbitmq-server`  
7. With RabbitMQ server running (it will after first install otherwise run it using `sudo rabbitmq-server`)  
    ```bash
    sudo rabbitmqctl add_user dev mypassword
    ```  
    ```bash
    sudo rabbitmqctl add_vhost db_tasks
    ```  
    ```bash
    sudo rabbitmqctl set_user_tags dev database_tasks
    ```  
    ```bash
    sudo rabbitmqctl set_permissions -p db_tasks dev ".*" ".*" ".*"
    ```  
   Substitute `mypassword` with a good password and update the password in `CELERY_BROKER_URL` variable in .env file acquired in the next step
6. Get the enviorment file from Yash or Nate for accessing the important environment variables.

You're good to go!
