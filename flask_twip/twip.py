#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

from __future__ import unicode_literals,\
    absolute_import, division, print_function

import requests
from flask import request as req
from flask import redirect, url_for, Blueprint,\
    session, request
from flask.ext.oauth import OAuth, OAuthException

import random
import string
import json
import os


class Twip(object):

    def __init__(self, app=None, url='/twip', backend=None):
        self.url = url
        self.bp = Blueprint('twip', __name__, url_prefix=self.url)
        if app is not None:
            self.app = app
            self.init_app(self.app)
        else:
            self.app = None

        self.backend = backend

    def getMapper(self):
        m = (
            ('/o/<path:path>', self.OMode),
            ('/t/<path:path>', self.TMode),
            ('/o/', self.redirect),
            ('/t/', self.redirect),
            ('/', self.index),
            ('/oauth/start/', self.oauth_start),
            ('/oauth/callback/', self.oauth_callback),
            ('/show_api/', self.show_api),
        )
        return m

    def init_app(self, app):
        self.app = app

        for (url, func) in self.getMapper():
            self.bp.add_url_rule(url, view_func=func)

        self.app.register_blueprint(self.bp)
        oauth = OAuth()

        self.twitter = oauth.remote_app(
            'twitter',
            base_url='https://api.twitter.com/1/',
            request_token_url='https://api.twitter.com/oauth/request_token',
            access_token_url='https://api.twitter.com/oauth/access_token',
            authorize_url='https://api.twitter.com/oauth/authenticate',
            consumer_key=self.app.config.get('TWITTER_CONSUMER_KEY'),
            consumer_secret=self.app.config.get('TWITTER_CONSUMER_SECRET'),
        )
        self.twitter.tokengetter(self.tokengetter)

    def tokengetter(self):
        return None
        #return (
        #    self.app.config.get('TWITTER_CONSUMER_SECRET'),
        #    self.app.config.get('TWITTER_CONSUMER_KEY'),
        #)

    def OMode(self, path):
        return path

    def TMode(self, path):
        return path

    def redirect(self):
        return redirect(url_for('twip.index'))

    def index(self):
        return 'index'

    def oauth_start(self):
        return self.twitter.authorize(callback=url_for('twip.oauth_callback'))

    def oauth_callback(self):
        try:
            if 'oauth_verifier' in request.args:
                data = self.twitter.handle_oauth1_response()
            elif 'code' in request.args:
                data = self.twitter.handle_oauth2_response()
            else:
                data = self.twitter.handle_unknown_response()
        except OAuthException as e:
            return redirect(url_for('twip.index'))
        self.twitter.free_request_token()

        key = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(5))

        self.backend.save(data['screen_name'], key, json.dumps(data))
        prefix = os.path.dirname(self.app.url_map._rules_by_endpoint['twip.OMode'][0].rule)

        url = '%s://%s%s/%s.%s' % (
            request.environ['wsgi.url_scheme'],
            request.environ['HTTP_HOST'],
            prefix,
            data['screen_name'],
            key
        )

        return redirect(url_for('twip.show_api')+'?api=%s' % (url,))

    def show_api(self):
        return request.args['api']
