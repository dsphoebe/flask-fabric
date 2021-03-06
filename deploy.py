# -*- coding: utf-8 -*-
from datetime import datetime
import os.path

from fabric.api import env, sudo, run, cd, prefix
from fabric.colors import green
from fabric.contrib.files import exists, sed
from fabric.operations import put

from .utils import mkdir

from .config import (
    NAME, DOMAIN, REPOSITORY, DEFAULT_BRANCH, WEB_ROOT_DIR, PYTHON,
    VIRTUALENV_NAME, SOCKET, UWSGI_LOG_DIR, WEB_LOG_DIR, TOUCH_FILE,
    ENVIRONMENT, NGINX_CONF, SUPERVISOR_CONF, PIP_UPGRADE)


def setup_dirs():
    if mkdir(WEB_ROOT_DIR, use_sudo=True):
        sudo('chown -R {0}:{0} {1}'.format(env.user, WEB_ROOT_DIR))

    with cd(WEB_ROOT_DIR):
        if not exists('www'):
            dir_name = 'www.' + datetime.now().strftime('%Y%m%d%H%M%S')
            run('git clone {} {}'.format(REPOSITORY, dir_name))
            run('ln -s {} www'.format(dir_name))

            if DEFAULT_BRANCH and DEFAULT_BRANCH != 'master':
                with cd(os.path.join(WEB_ROOT_DIR, 'www')):
                    run('git checkout -t origin/' + DEFAULT_BRANCH)

    mkdir(UWSGI_LOG_DIR, use_sudo=True)
    mkdir(WEB_LOG_DIR, use_sudo=True)


def mkvirtualenv():
    if exists('~/.virtualenvs/{}'.format(VIRTUALENV_NAME)):
        return
    # with prefix('WORKON_HOME=$HOME/.virtualenvs'):
    with prefix('source /usr/local/bin/virtualenvwrapper.sh'):
        run('mkvirtualenv -p {} {}'.format(PYTHON, VIRTUALENV_NAME))


def git_pull():
    with cd(os.path.join(WEB_ROOT_DIR, 'www')):
        run('git pull')


def install_requirements():
    # with prefix('workon {}'.format(VIRTUALENV_NAME)):
    with cd(os.path.join(WEB_ROOT_DIR, 'www')):
        with prefix('source ~/.virtualenvs/{}/bin/activate'
                    .format(VIRTUALENV_NAME)):
            if PIP_UPGRADE:
                run('pip install -q -U -r requirements.txt')
            else:
                run('pip install -q -r requirements.txt')


def config_supervisor():
    print(green('config supervisor'))

    conf_name = NAME + '.conf'
    remote_path = '/etc/supervisor/conf.d/{}'.format(conf_name)

    if not exists(remote_path):
        put(SUPERVISOR_CONF, remote_path, use_sudo=True)
        sed(remote_path, '<name>', NAME, use_sudo=True, backup='')
        uwsgi_ini_file = os.path.join(WEB_ROOT_DIR, 'www/uwsgi.ini')
        sed(remote_path, '<environment>', ENVIRONMENT,
            use_sudo=True, backup='')
        sed(remote_path, '<uwsgi_ini_file>', uwsgi_ini_file,
            use_sudo=True, backup='')
    sudo('supervisorctl reread')
    sudo('supervisorctl update')


def config_nginx():
    print(green('config nginx'))

    remote_path = '/etc/nginx/sites-available/{}'.format(NAME)

    if not exists(remote_path):
        put(NGINX_CONF, remote_path, use_sudo=True)
        sed(remote_path, '<name>', NAME, use_sudo=True, backup='')
        sed(remote_path, '<domain>', DOMAIN, use_sudo=True, backup='')
        sed(remote_path, '<socket>', SOCKET, use_sudo=True, backup='')
        with cd('/etc/nginx/sites-enabled'):
            if not exists(NAME):
                sudo('ln -s {} {}'.format(remote_path, NAME))

    sudo('nginx -s reload')


def restart():
    if TOUCH_FILE:
        sudo('touch {}'.format(TOUCH_FILE))
    else:
        sudo('supervisorctl restart {}'.format(NAME))
