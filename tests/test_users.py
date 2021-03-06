# Copyright (C) 2017  Secured By THEM
# Original Author: Michael Casadevall <michaelc@them.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import logging
import os

import psycopg2

import bcrypt
import ndr_server
import ndr_webui
import tests.common

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_CONFIG = THIS_DIR + "/test_config.yml"
TEST_FLASK_CONFIG = THIS_DIR + "/flask_test_config.cfg"


class TestUsers(unittest.TestCase):
    '''Test user object behaviors'''

    @classmethod
    def setUpClass(cls):
        # Setup Flask basic configuration
        flask_app = ndr_webui.init_app(testing=True,
                                       config_file=TEST_FLASK_CONFIG)
        cls.flask_app = flask_app
        cls.app = flask_app.test_client()

    def test_get_admin_user(self):
        '''Tests getting the admin user'''
        with self.flask_app.app_context():
            user = tests.common.create_admin_user(self)
            db_conn = ndr_webui.config.get_db_connection()

            admin_user = ndr_webui.User.read_by_id(ndr_webui.NSC,
                                                   user.pg_id,
                                                   db_conn=db_conn)

            self.assertEqual(tests.common.ROOT_USERNAME, admin_user.username)
            self.assertEqual(tests.common.ROOT_REAL_NAME, admin_user.real_name)
            self.assertEqual(tests.common.ROOT_EMAIL, admin_user.email)
            self.assertTrue(admin_user.is_active)
            self.assertTrue(admin_user.check_password(tests.common.ROOT_PW))

    def test_get_admin_user_by_email(self):
        '''Tests getting a user by email address'''
        with self.flask_app.app_context():
            tests.common.create_admin_user(self)
            db_conn = ndr_webui.config.get_db_connection()

            admin_user = ndr_webui.User.read_by_email(ndr_webui.NSC,
                                                      tests.common.ROOT_EMAIL,
                                                      db_conn=db_conn)

            self.assertEqual(tests.common.ROOT_USERNAME, admin_user.username)
            self.assertEqual(tests.common.ROOT_REAL_NAME, admin_user.real_name)
            self.assertEqual(tests.common.ROOT_EMAIL, admin_user.email)
            self.assertTrue(admin_user.is_active)
            self.assertTrue(admin_user.check_password(tests.common.ROOT_PW))

    def test_check_invalid_password(self):
        '''Tests that we properly error out on invalid passwords'''
        with self.flask_app.app_context():
            user = tests.common.create_admin_user(self)
            db_conn = ndr_webui.config.get_db_connection()

            admin_user = ndr_webui.User.read_by_id(ndr_webui.NSC,
                                                   user.pg_id,
                                                   db_conn=db_conn)
            self.assertFalse(admin_user.check_password("not the right PW"))

    def test_invalid_user(self):
        '''Tests that we properly error out on invalid passwords'''
        with self.flask_app.app_context():
            db_conn = ndr_webui.config.get_db_connection()

            self.assertRaises(psycopg2.InternalError,
                              ndr_webui.User.read_by_id,
                              ndr_webui.NSC,
                              1337,
                              db_conn=db_conn)

    def test_get_organizations_for_user(self):
        '''Tests that we can get all organizations for a user'''
        with self.flask_app.app_context():
            nsc = ndr_webui.config.get_ndr_server_config()
            db_conn = ndr_webui.config.get_db_connection()

            # First we need to create a test organization
            org = ndr_server.Organization.create(
                nsc,
                "Test Org",
                db_conn=db_conn
            )

            # The admin is a superuser, we should see all organizations
            user = tests.common.create_admin_user(self)
            admin_user = ndr_webui.User.read_by_id(ndr_webui.NSC,
                                                   user.pg_id,
                                                   db_conn=db_conn)
            user_orgs = admin_user.get_organizations_for_user(db_conn=db_conn)

            # If we're running on an existing DB, we might get more than one
            self.assertGreaterEqual(len(user_orgs), 1)

            # Make sure our test organization is in there
            self.assertIn(org, user_orgs)

    def test_creating_new_user(self):
        '''Tests new user creation'''
        with self.flask_app.app_context():
            admin_user = tests.common.create_admin_user(self)
            new_user = tests.common.create_unprivilleged_user(self, admin_user)

            self.assertEqual(tests.common.NO_ACL_USER, new_user.username)
            self.assertEqual(tests.common.NO_ACL_REAL_NAME, new_user.real_name)
            self.assertEqual(tests.common.NO_ACL_EMAIL, new_user.email)
            self.assertTrue(new_user.check_password(
                tests.common.NO_ACL_PASSWORD))

    def test_acl_failure_create_user(self):
        '''Tests that user creation fails with unprivilleged user'''
        with self.flask_app.app_context():
            nsc = ndr_webui.config.get_ndr_server_config()
            db_conn = ndr_webui.config.get_db_connection()

            admin_user = tests.common.create_admin_user(self)
            new_user = tests.common.create_unprivilleged_user(self, admin_user)

            self.assertRaises(
                psycopg2.InternalError,
                ndr_webui.User.create,
                nsc,
                new_user,
                "failuser",
                "failuser@fail.com",
                "someuncryptedpw",
                "Fail User",
                db_conn
            )

    def test_get_sites_for_user(self):
        '''Tests that we can get all organizations for a user'''
        with self.flask_app.app_context():
            db_conn = ndr_webui.config.get_db_connection()

            # First we need to create a test organization
            org = tests.common.create_organization(self, "test org")

            # And a site
            site = tests.common.create_site(self, org, "test site")

            # The admin is a superuser, we should see all organizations
            admin_user = tests.common.create_admin_user(self)
            user_sites = admin_user.get_sites_in_organization_for_user(org, db_conn)

            # If we're running on an existing DB, we might get more than one
            self.assertGreaterEqual(len(user_sites), 1)

            # Make sure our test organization is in there
            self.assertIn(site, user_sites)

    def test_get_recorders_for_user(self):
        '''Tests that we can get all recorders for a user in a site'''
        with self.flask_app.app_context():
            db_conn = ndr_webui.config.get_db_connection()

            # First we need to create a test organization
            org = tests.common.create_organization(self, "test org")

            # And a site
            site = tests.common.create_site(self, org, "test site")

            # And now the recorder
            recorder = tests.common.create_recorder(self, site, "Test Recorder", "ndr_web_test")

            # The admin is a superuser, we should see all organizations
            admin_user = tests.common.create_admin_user(self)
            user_recorders = admin_user.get_recorders_in_site_for_user(site, db_conn)

            # If we're running on an existing DB, we might get more than one
            self.assertGreaterEqual(len(user_recorders), 1)

            # Make sure our test organization is in there
            self.assertIn(recorder, user_recorders)
