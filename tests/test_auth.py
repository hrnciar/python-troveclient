import contextlib

from testtools import TestCase
from reddwarfclient import auth
from mock import Mock

from reddwarfclient import exceptions

"""
Unit tests for the classes and functions in auth.py.
"""


def check_url_none(test_case, auth_class):
    # url is None, it must throw exception
    authObj = auth_class(url=None, type=auth_class, client=None,
                         username=None, password=None, tenant=None)
    try:
        authObj.authenticate()
        test_case.fail("AuthUrlNotGiven exception expected")
    except exceptions.AuthUrlNotGiven:
        pass


class AuthenticatorTest(TestCase):

    def setUp(self):
        super(AuthenticatorTest, self).setUp()
        self.orig_load = auth.ServiceCatalog._load
        self.orig__init = auth.ServiceCatalog.__init__

    def tearDown(self):
        super(AuthenticatorTest, self).tearDown()
        auth.ServiceCatalog._load = self.orig_load
        auth.ServiceCatalog.__init__ = self.orig__init

    def test_get_authenticator_cls(self):
        class_list = (auth.KeyStoneV2Authenticator,
                      auth.RaxAuthenticator,
                      auth.Auth1_1,
                      auth.FakeAuth)

        for c in class_list:
            self.assertEqual(c, auth.get_authenticator_cls(c))

        class_names = {"keystone": auth.KeyStoneV2Authenticator,
                       "rax": auth.RaxAuthenticator,
                       "auth1.1": auth.Auth1_1,
                       "fake": auth.FakeAuth}

        for cn in class_names.keys():
            self.assertEqual(class_names[cn], auth.get_authenticator_cls(cn))

        cls_or_name = "_unknown_"
        self.assertRaises(ValueError, auth.get_authenticator_cls, cls_or_name)

    def test__authenticate(self):
        authObj = auth.Authenticator(Mock(), auth.KeyStoneV2Authenticator,
                                     Mock(), Mock(), Mock(), Mock())
        # test response code 200
        resp = Mock()
        resp.status = 200
        body = "test_body"

        auth.ServiceCatalog._load = Mock(return_value=1)
        authObj.client._time_request = Mock(return_value=(resp, body))

        sc = authObj._authenticate(Mock(), Mock())
        self.assertEqual(body, sc.catalog)

        # test AmbiguousEndpoints exception
        auth.ServiceCatalog.__init__ = \
            Mock(side_effect=exceptions.AmbiguousEndpoints)
        self.assertRaises(exceptions.AmbiguousEndpoints,
                          authObj._authenticate, Mock(), Mock())

        # test handling KeyError and raising AuthorizationFailure exception
        auth.ServiceCatalog.__init__ = Mock(side_effect=KeyError)
        self.assertRaises(exceptions.AuthorizationFailure,
                          authObj._authenticate, Mock(), Mock())

        # test EndpointNotFound exception
        mock = Mock(side_effect=exceptions.EndpointNotFound)
        auth.ServiceCatalog.__init__ = mock
        self.assertRaises(exceptions.EndpointNotFound,
                          authObj._authenticate, Mock(), Mock())
        mock.side_effect = None

        # test response code 305
        resp.__getitem__ = Mock(return_value='loc')
        resp.status = 305
        body = "test_body"
        authObj.client._time_request = Mock(return_value=(resp, body))

        l = authObj._authenticate(Mock(), Mock())
        self.assertEqual('loc', l)

        # test any response code other than 200 and 305
        resp.status = 404
        exceptions.from_response = Mock(side_effect=ValueError)
        self.assertRaises(ValueError, authObj._authenticate, Mock(), Mock())

    def test_authenticate(self):
        authObj = auth.Authenticator(Mock(), auth.KeyStoneV2Authenticator,
                                     Mock(), Mock(), Mock(), Mock())
        self.assertRaises(NotImplementedError, authObj.authenticate)


class KeyStoneV2AuthenticatorTest(TestCase):

    def test_authenticate(self):
        # url is None
        check_url_none(self, auth.KeyStoneV2Authenticator)

        # url is not None, so it must not throw exception
        url = "test_url"
        cls_type = auth.KeyStoneV2Authenticator
        authObj = auth.KeyStoneV2Authenticator(url=url, type=cls_type,
                                               client=None, username=None,
                                               password=None, tenant=None)

        def side_effect_func(url):
            return url

        mock = Mock()
        mock.side_effect = side_effect_func
        authObj._v2_auth = mock
        r = authObj.authenticate()
        self.assertEqual(url, r)

    def test__v2_auth(self):
        username = "reddwarf_user"
        password = "reddwarf_password"
        tenant = "tenant"
        cls_type = auth.KeyStoneV2Authenticator
        authObj = auth.KeyStoneV2Authenticator(url=None, type=cls_type,
                                               client=None,
                                               username=username,
                                               password=password,
                                               tenant=tenant)

        def side_effect_func(url, body):
            return body
        mock = Mock()
        mock.side_effect = side_effect_func
        authObj._authenticate = mock
        body = authObj._v2_auth(Mock())
        self.assertEqual(username,
                         body['auth']['passwordCredentials']['username'])
        self.assertEqual(password,
                         body['auth']['passwordCredentials']['password'])
        self.assertEqual(tenant, body['auth']['tenantName'])


class Auth1_1Test(TestCase):

    def test_authenticate(self):
        # handle when url is None
        check_url_none(self, auth.Auth1_1)

        # url is not none
        username = "reddwarf_user"
        password = "reddwarf_password"
        url = "test_url"
        authObj = auth.Auth1_1(url=url,
                               type=auth.Auth1_1,
                               client=None, username=username,
                               password=password, tenant=None)

        def side_effect_func(auth_url, body, root_key):
            return auth_url, body, root_key

        mock = Mock()
        mock.side_effect = side_effect_func
        authObj._authenticate = mock
        auth_url, body, root_key = authObj.authenticate()

        self.assertEqual(username, body['credentials']['username'])
        self.assertEqual(password, body['credentials']['key'])
        self.assertEqual(auth_url, url)
        self.assertEqual('auth', root_key)


class RaxAuthenticatorTest(TestCase):

    def test_authenticate(self):
        # url is None
        check_url_none(self, auth.RaxAuthenticator)

        # url is not None, so it must not throw exception
        url = "test_url"
        authObj = auth.RaxAuthenticator(url=url,
                                        type=auth.RaxAuthenticator,
                                        client=None, username=None,
                                        password=None, tenant=None)

        def side_effect_func(url):
            return url

        mock = Mock()
        mock.side_effect = side_effect_func
        authObj._rax_auth = mock
        r = authObj.authenticate()
        self.assertEqual(url, r)

    def test__rax_auth(self):
        username = "reddwarf_user"
        password = "reddwarf_password"
        tenant = "tenant"
        authObj = auth.RaxAuthenticator(url=None,
                                        type=auth.RaxAuthenticator,
                                        client=None, username=username,
                                        password=password, tenant=tenant)

        def side_effect_func(url, body):
            return body

        mock = Mock()
        mock.side_effect = side_effect_func
        authObj._authenticate = mock
        body = authObj._rax_auth(Mock())

        v = body['auth']['RAX-KSKEY:apiKeyCredentials']['username']
        self.assertEqual(username, v)

        v = body['auth']['RAX-KSKEY:apiKeyCredentials']['apiKey']
        self.assertEqual(password, v)

        v = body['auth']['RAX-KSKEY:apiKeyCredentials']['tenantName']
        self.assertEqual(tenant, v)


class FakeAuthTest(TestCase):

    def test_authenticate(self):
        tenant = "tenant"
        authObj = auth.FakeAuth(url=None,
                                type=auth.FakeAuth,
                                client=None, username=None,
                                password=None, tenant=tenant)

        fc = authObj.authenticate()
        public_url = "%s/%s" % ('http://localhost:8779/v1.0', tenant)
        self.assertEqual(public_url, fc.get_public_url())
        self.assertEqual(tenant, fc.get_token())


class ServiceCatalogTest(TestCase):

    def setUp(self):
        super(ServiceCatalogTest, self).setUp()
        self.orig_url_for = auth.ServiceCatalog._url_for
        self.orig__init__ = auth.ServiceCatalog.__init__
        auth.ServiceCatalog.__init__ = Mock(return_value=None)
        self.test_url = "http://localhost:1234/test"

    def tearDown(self):
        super(ServiceCatalogTest, self).tearDown()
        auth.ServiceCatalog._url_for = self.orig_url_for
        auth.ServiceCatalog.__init__ = self.orig__init__

    def test__load(self):
        url = "random_url"
        auth.ServiceCatalog._url_for = Mock(return_value=url)

        # when service_url is None
        scObj = auth.ServiceCatalog()
        scObj.region = None
        scObj.service_url = None
        scObj._load()
        self.assertEqual(url, scObj.public_url)
        self.assertEqual(url, scObj.management_url)

        # service url is not None
        service_url = "service_url"
        scObj = auth.ServiceCatalog()
        scObj.region = None
        scObj.service_url = service_url
        scObj._load()
        self.assertEqual(service_url, scObj.public_url)
        self.assertEqual(service_url, scObj.management_url)

    def test_get_token(self):
        test_id = "test_id"
        scObj = auth.ServiceCatalog()
        scObj.root_key = "root_key"
        scObj.catalog = dict()
        scObj.catalog[scObj.root_key] = dict()
        scObj.catalog[scObj.root_key]['token'] = dict()
        scObj.catalog[scObj.root_key]['token']['id'] = test_id
        self.assertEqual(test_id, scObj.get_token())

    def test_get_management_url(self):
        test_mng_url = "test_management_url"
        scObj = auth.ServiceCatalog()
        scObj.management_url = test_mng_url
        self.assertEqual(test_mng_url, scObj.get_management_url())

    def test_get_public_url(self):
        test_public_url = "test_public_url"
        scObj = auth.ServiceCatalog()
        scObj.public_url = test_public_url
        self.assertEqual(test_public_url, scObj.get_public_url())

    def test__url_for(self):
        scObj = auth.ServiceCatalog()

        # case for no endpoint found
        self.case_no_endpoint_match(scObj)

        # case for empty service catalog
        self.case_endpoing_with_empty_catalog(scObj)

        # more than one matching endpoints
        self.case_ambiguous_endpoint(scObj)

        # happy case
        self.case_unique_endpoint(scObj)

        # testing if-statements in for-loop to iterate services in catalog
        self.case_iterating_services_in_catalog(scObj)

    def case_no_endpoint_match(self, scObj):
        # empty endpoint list
        scObj.catalog = dict()
        scObj.catalog['endpoints'] = list()
        self.assertRaises(exceptions.EndpointNotFound, scObj._url_for)

        def side_effect_func_ep(attr):
            return "test_attr_value"

        # simulating dict
        endpoint = Mock()
        mock = Mock()
        mock.side_effect = side_effect_func_ep
        endpoint.__getitem__ = mock
        scObj.catalog['endpoints'].append(endpoint)

        # not-empty list but not matching endpoint
        filter_value = "not_matching_value"
        self.assertRaises(exceptions.EndpointNotFound, scObj._url_for,
                          attr="test_attr", filter_value=filter_value)

        filter_value = "test_attr_value"  # so that we have an endpoint match
        scObj.root_key = "access"
        scObj.catalog[scObj.root_key] = dict()
        self.assertRaises(exceptions.EndpointNotFound, scObj._url_for,
                          attr="test_attr", filter_value=filter_value)

    def case_endpoing_with_empty_catalog(self, scObj):
        # first, test with empty catalog, this should pass since
        # there is already enpoint added
        scObj.catalog[scObj.root_key]['serviceCatalog'] = list()

        endpoint = scObj.catalog['endpoints'][0]
        endpoint.get = Mock(return_value=self.test_url)
        r_url = scObj._url_for(attr="test_attr",
                               filter_value="test_attr_value")
        self.assertEqual(self.test_url, r_url)

    def case_ambiguous_endpoint(self, scObj):
        scObj.service_type = "reddwarf"
        scObj.service_name = "test_service_name"

        def side_effect_func_service(key):
            if key == "type":
                return "reddwarf"
            elif key == "name":
                return "test_service_name"
            return None

        mock1 = Mock()
        mock1.side_effect = side_effect_func_service
        service1 = Mock()
        service1.get = mock1

        endpoint2 = {"test_attr": "test_attr_value"}
        service1.__getitem__ = Mock(return_value=[endpoint2])
        scObj.catalog[scObj.root_key]['serviceCatalog'] = [service1]
        self.assertRaises(exceptions.AmbiguousEndpoints, scObj._url_for,
                          attr="test_attr", filter_value="test_attr_value")

    def case_unique_endpoint(self, scObj):
        # changing the endpoint2 attribute to pass the filter
        service1 = scObj.catalog[scObj.root_key]['serviceCatalog'][0]
        endpoint2 = service1[0][0]
        endpoint2["test_attr"] = "new value not matching filter"
        r_url = scObj._url_for(attr="test_attr",
                               filter_value="test_attr_value")
        self.assertEqual(self.test_url, r_url)

    def case_iterating_services_in_catalog(self, scObj):
        service1 = scObj.catalog[scObj.root_key]['serviceCatalog'][0]

        scObj.catalog = dict()
        scObj.root_key = "access"
        scObj.catalog[scObj.root_key] = dict()
        scObj.service_type = "no_match"

        scObj.catalog[scObj.root_key]['serviceCatalog'] = [service1]
        self.assertRaises(exceptions.EndpointNotFound, scObj._url_for)

        scObj.service_type = "database"
        scObj.service_name = "no_match"
        self.assertRaises(exceptions.EndpointNotFound, scObj._url_for)

        # no endpoints and no 'serviceCatalog' in catalog => raise exception
        scObj = auth.ServiceCatalog()
        scObj.catalog = dict()
        scObj.root_key = "access"
        scObj.catalog[scObj.root_key] = dict()
        scObj.catalog[scObj.root_key]['serviceCatalog'] = []
        self.assertRaises(exceptions.EndpointNotFound, scObj._url_for,
                          attr="test_attr", filter_value="test_attr_value")
