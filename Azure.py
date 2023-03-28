import json
from urllib.parse import quote_plus
import requests
import msal
import os
import time
from datetime import datetime


class Azure():

    def __init__(self, tenant_id, client_id, secret):
        self.__tenant_id = tenant_id
        self.__client_id = client_id
        self.__secret = secret
        self.__header = None
        self.__hostpool_api_version = "2022-02-10-preview"
        self.__virtual_machine_api_version = "2022-11-01"
        self.__virtual_network_api_version = "2022-07-01"
        self.user_fields = '&$select=accountEnabled,ageGroup,assignedLicenses,assignedPlans,assignedPlans,' \
                           'assignedPlans,businessPhones,city,companyName,consentProvidedForMinor,country,' \
                           'createdDateTime,createdObjects,creationType,department,displayName,employeeHireDate,' \
                           'employeeId,employeeOrgData,costCenter,employeeOrgData,division,employeeType,' \
                           'externalUserState,faxNumber,givenName,identities,imAddresses,isResourceAccount,' \
                           'jobTitle,mail,mailNickname,manager,id,mobilePhone,officeLocation,' \
                           'onPremisesExtensionAttributes,extensionAttribute,onPremisesImmutableId,' \
                           'onPremisesLastSyncDateTime,onPremisesProvisioningErrors,onPremisesProvisioningErrors,' \
                           'onPremisesSamAccountName,onPremisesSecurityIdentifier,onPremisesSyncEnabled,otherMails,' \
                           'passwordPolicies,passwordProfile,forceChangePasswordNextSignIn,passwordProfile,' \
                           'forceChangePasswordNextSignInWithMfa,postalCode,preferredLanguage,provisionedPlans,' \
                           'provisionedPlans,proxyAddresses,showInAddressList,state,streetAddress,surname,' \
                           'usageLocation,userPrincipalName,userType,region'
        self.group_fields = None
        self.__token_expiration = None
        self.__management_type_url: str

    def __get_auth_token(self, management_type_url):
        """
        Checks if bearer token expiration exists or if token is expired. Returns bearer token and sets __token_expiration.

        params: managementTypeUrl - What management type to target, example: "https://management.azure.com"
        """
        TIME_NOW = int(datetime.now().timestamp())
        if not self.__token_expiration or int(
                self.__token_expiration) < TIME_NOW or management_type_url != self.__management_type_url:
            print("creating token")
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.__client_id,
                "client_secret": self.__secret,
                "resource": management_type_url,
            }
            r = requests.post(

                "https://login.microsoftonline.com/"
                + self.__tenant_id
                + "/oauth2/token",
                payload,
            )
            token = json.loads(r.content).get("access_token")
            token_expiration = json.loads(r.content).get("expires_on")
            self.__management_type_url = management_type_url
            self.__token = token
            self.__token_expiration = token_expiration
            self.__header = {'Authorization': f'Bearer {token}'}
        return self.__token

    def auth(self):
        token = self.__get_auth_token("https://management.azure.com")


    def auth_default(self,
             scope=None,
             authority=None):

        if not authority:
            authority = 'https://login.microsoftonline.com/' + self.__tenant_id
        if not scope:
            scope = ["https://graph.microsoft.com/.default"]

        app = msal.ConfidentialClientApplication(self.__client_id, authority=authority, client_credential=self.__secret)
        result = app.acquire_token_for_client(scopes=scope)

        if "access_token" in result:
            self.__header = {'Authorization': 'Bearer ' + result['access_token']}
            return {"Action": "Successful"}
        else:
            print(result.get("error"))
            print(result.get("error_description"))
            print(result.get("correlation_id"))  # You may need this when reporting a bug
            return {"Action": "Failed",
                    'error': result.get("error"),
                    "description": result.get("error_description"),
                    "correlation_id": result.get("correlation_id")}

    def auth_as_user(self, scope=None, authority=None):
        if not authority:
            authority = 'https://login.microsoftonline.com/' + self.__tenant_id
        if not scope:
            scope = ["https://graph.microsoft.com/.default"]

        app = msal.PublicClientApplication(client_id=self.__client_id, authority=authority)
        flow = app.initiate_device_flow(scopes=scope)

        if "user_code" not in flow:
            raise ValueError("Fail to create device flow. Err: %s" % json.dumps(flow, indent=4))

        print(flow["message"])

        result = app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            self.__header = {'Authorization': 'Bearer ' + result['access_token']}
            return {"Action": "Successful",
                    "raw": result}
        else:
            print(result.get("error"))
            print(result.get("error_description"))
            print(result.get("correlation_id"))  # You may need this when reporting a bug
            return {"Action": "Failed",
                    'error': result.get("error"),
                    "description": result.get("error_description"),
                    "correlation_id": result.get("correlation_id"),
                    "raw": result}

    def _set_header(self, header=None, override=None):
        if not header:
            header = self.__header
        else:
            if "Authorization" not in header:
                if self.__header:
                    if 'Authorization' in self.__header:
                        header['Authorization'] = self.__header['Authorization']
        if override:
            for key in override:
                header[key] = override[key]
            self.__header = header
        return header

    def get_all_users(self, disabled_users=False, header=None):
        url = 'https://graph.microsoft.com/v1.0/users?' + self.user_fields

        header = self._set_header(header)

        all_users = []

        # Make initial request
        response = requests.get(url, headers=header).json()

        # while response is not None
        print("Retrieved / Total")
        while response:
            # add to all users above
            # print(response['value'])
            print(len(response['value']), "/", len(all_users))
            all_users += response['value']
            # ask for next request if the request has nextlink in return. if there was no else, it will return none in
            # the next while loop and exit
            response = requests.get(response['@odata.nextLink'],
                                    headers=header).json() if '@odata.nextLink' in response else None

        if disabled_users:
            all_users += self.get_all_disabled_users()

        return all_users

    def get_all_disabled_users(self, header=None):
        url = 'https://graph.microsoft.com/v1.0/directory/deletedItems/microsoft.graph.user?' + self.user_fields

        header = self._set_header(header)

        all_users = []

        # Make initial request
        response = requests.get(url, headers=header).json()

        # while response is not None
        while response:
            # add to all users above
            print(response['value'])
            print(len(all_users))
            all_users += response['value']
            # ask for next request if the request has nextlink in return. if there was no else, it will return none in
            # the next while loop and exit
            response = requests.get(response['@odata.nextLink'],
                                    headers=header).json() if '@odata.nextLink' in response else None

        return all_users

    def get_all_groups(self, header=None):
        url = "https://graph.microsoft.com/v1.0/groups"
        header = self._set_header(header)
        all_users = []
        # Make initial request
        response = requests.get(url, headers=header).json()
        # while response is not None
        while response:
            # add to all users above
            print(response['value'])
            print(len(all_users))
            all_users += response['value']
            # ask for next request if the request has nextlink in return. if there was no else, it will return none in
            # the next while loop and exit
            response = requests.get(response['@odata.nextLink'],
                                    headers=header).json() if '@odata.nextLink' in response else None
        return all_users

    def get_displayname(self, displayname, exact_match=True, memberof=False, header=None):
        new_displayname = displayname.replace(" ", '%20')
        url = 'https://graph.microsoft.com/v1.0/users?$count=true&$search=%22displayName:{name}%22'.format(
            name=new_displayname) + self.user_fields

        header = self._set_header(header)
        # required for this url
        header['ConsistencyLevel'] = 'Eventual'

        # Make initial request
        response = requests.get(url, headers=header).json()
        # check if its EXACT value
        if 'value' in response:
            # check if its EXACT value
            if exact_match:
                found_flag = False
                for item in response['value']:
                    if item['displayName'].lower() == displayname.lower():
                        found_flag = True
                        response['value'] = [item]
                        break
                if not found_flag:
                    response['value'] = []
                    return response

            # Go through all results
            if memberof:
                for num in range(len(response['value'])):
                    if 'id' in response['value'][num]:
                        # set empty list inside the users earlier response
                        response['value'][num]['memberOf'] = []

                        url = 'https://graph.microsoft.com/v1.0/users/{user_id}/memberOf?$count=true&'.format(
                            user_id=response['value'][num]['id'])

                        user_response = requests.get(url, headers=header).json()
                        if '@odata.nextLink' in user_response:
                            while user_response:
                                # add to all users above
                                response['value'][num]['memberOf'] += user_response['value']
                                # ask for next request if the request has nextlink in return. if there was no else,
                                # it will return none in
                                # the next while loop and exit
                                user_response = requests.get(user_response['@odata.nextLink'],
                                                             headers=header).json() \
                                    if '@odata.nextLink' in user_response \
                                    else None
        return response

    def get_username(self, username, exact_match=True, memberof=False, header=None):
        url = 'https://graph.microsoft.com/v1.0/users?$count=true&$search=' \
              '%22userPrincipalName:{name}%22'.format(name=username) + self.user_fields

        header = self._set_header(header)
        # Required for this url
        header['ConsistencyLevel'] = 'Eventual'

        # Make initial request
        response = requests.get(url, headers=header).json()
        # check if its EXACT value
        if 'value' in response:
            # check if its EXACT value
            if exact_match:
                found_flag = False
                for item in response['value']:
                    if item['userPrincipalName'].lower().split("@")[0] == username.lower():
                        found_flag = True
                        response['value'] = [item]
                        break
                if not found_flag:
                    response['value'] = []
                    return response

            # Go through all results
            if memberof:
                for num in range(len(response['value'])):
                    if 'id' in response['value'][num]:
                        response['value'][num]['memberOf'] = []
                        url = 'https://graph.microsoft.com/v1.0/users/{user_id}/memberOf?$count=true&'.format(
                            user_id=response['value'][num]['id'])
                        user_response = requests.get(url, headers=header).json()

                        if '@odata.nextLink' in user_response:
                            while user_response:
                                # add to all users above
                                response['value'][num]['memberOf'] += user_response['value']
                                # ask for next request if the request has nextlink in return.
                                # if there was no else, it will return none in the next while loop and exit
                                user_response = requests.get(user_response['@odata.nextLink'],
                                                             headers=header).json() if '@odata.nextLink' in \
                                                                                       user_response else None
        return response

    def get_user_by_id(self, user_id, memberof=False, header=None):
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}?" + self.user_fields

        header = self._set_header(header)
        # Required for this url
        header['ConsistencyLevel'] = 'Eventual'

        # Make initial request
        response = requests.get(url, headers=header).json()
        # check if its EXACT value
        if 'value' in response:
            # Go through all results
            if memberof:
                for num in range(len(response['value'])):
                    if 'id' in response['value'][num]:
                        response['value'][num]['memberOf'] = []
                        url = 'https://graph.microsoft.com/v1.0/users/{user_id}/memberOf?$count=true&'.format(
                            user_id=response['value'][num]['id'])
                        user_response = requests.get(url, headers=header).json()

                        if '@odata.nextLink' in user_response:
                            while user_response:
                                # add to all users above
                                response['value'][num]['memberOf'] += user_response['value']
                                # ask for next request if the request has nextlink in return.
                                # if there was no else, it will return none in the next while loop and exit
                                user_response = requests.get(user_response['@odata.nextLink'],
                                                             headers=header).json() if '@odata.nextLink' in \
                                                                                       user_response else None
        return response

    def get_url(self, url, header=None):
        header = self._set_header(header)

        # Make initial request
        response = requests.get(url, headers=header).json()
        return response

    def get_group(self, displayname, exact_match=True, header=None):
        """
        :param displayname:
        :param exact_match:
        :param header:
        :return:
        """
        url = 'https://graph.microsoft.com/v1.0/groups?$count=true&$search=%22displayName:{name}%22'.format(
            name=displayname.replace(" ", '%20'))

        header = self._set_header(header)
        # Required for this url
        header['ConsistencyLevel'] = 'Eventual'

        # Make initial request
        response = requests.get(url, headers=header).json()

        # Grab members
        if 'value' in response:
            # check if its EXACT value
            if exact_match:
                found_flag = False
                for item in response['value']:
                    if item['displayName'].lower() == displayname.lower():
                        found_flag = True
                        response['value'] = [item]
                        break
                if not found_flag:
                    response['value'] = []
                    return response

            # Go through all results
            for num in range(len(response['value'])):
                if 'id' in response['value'][num]:
                    response['value'][num]['members'] = []
                    url = 'https://graph.microsoft.com/v1.0/groups/{group_id}/members?$count=true&'.format(
                        group_id=response['value'][num]['id'])
                    group_response = requests.get(url, headers=header).json()

                    while group_response:
                        # add to all users above
                        response['value'][num]['members'] += group_response['value']
                        # ask for next request if the request has nextlink in return.
                        # if there was no else, it will return none in the next while loop and exit
                        group_response = requests.get(group_response['@odata.nextLink'],
                                                      headers=header).json() if '@odata.nextLink' in \
                                                                                group_response else None

        return response

    def get_group_by_id(self, group_id, filter=None, header=None):
        """
        :param group_id:
        :param filter:
        :param header:
        :return:
        """
        url = f"https://graph.microsoft.com/v1.0//groups/{group_id}/members"
        if filter:
            url += filter
        header = self._set_header(header)
        # Required for this url
        header['ConsistencyLevel'] = 'Eventual'

        # Make initial request
        response = requests.get(url, headers=header).json()
        response_values = {'@odata.context': response['@odata.context'],
                           'value': response['value']}
        if '@odata.nextLink' in response:
            while response:
                if 'value' in response:
                    print(len(response_values['value']), response.keys(), response['value'][-1])
                    # add to all users above
                    response_values['value'] += response['value']
                # ask for next request if the request has nextlink in return.
                # if there was no else, it will return none in the next while loop and exit
                response = requests.get(response['@odata.nextLink'],
                                              headers=header).json() if '@odata.nextLink' in \
                                                                        response else None

        return response_values

    def add_user_to_group(self, group_id, user_email, header=None):
        """
        :param group_id:
        :param user_email:
        :param header:
        :return:
        """

        header = self._set_header(header)
        # Required for this url
        header['ConsistencyLevel'] = 'Eventual'
        header['Content-type'] = "application/json"

        if type(user_email) == str:
            url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members/$ref"
            payload = {"@odata.id": "https://graph.microsoft.com/v1.0/users/" + quote_plus(user_email)}
            response = requests.post(url, headers=header, data=json.dumps(payload))

            """
            Not sure what specific permission this needs to work, commenting out for now
            https://docs.microsoft.com/en-us/graph/api/group-post-members?view=graph-rest-1.0&tabs=http
            elif type(user_email) == list:
                url = f"https://graph.microsoft.com/v1.0/groups/{group_id}"
                payload = {"members@odata.bind": []}
                for user in user_email:
                    payload["members@odata.bind"].append("https://graph.microsoft.com/v1.0/users/" + quote_plus(user))
                response = requests.patch(url, headers=header, data=json.dumps(payload))
            """
        else:
            return {"Error:": "User email requires string value"}

        return response

    def remove_user_from_group(self, group_id, user_email, header=None):
        """
        :param group_id:
        :param user_email:
        :param header:
        :return:
        """

        header = self._set_header(header)
        # Required for this url
        header['ConsistencyLevel'] = 'Eventual'
        header['Content-type'] = "application/json"

        if type(user_email) == str:
            url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members/{quote_plus(user_email)}/$ref"
            response = requests.delete(url, headers=header)

        else:
            return {"Error:": "User email requires string value"}

        return response

    def get_device_id(self, device_id, header=None):
        """
        :param device_id:
        :param header:
        :return:
        """

        header = self._set_header(header)
        # Required for this url
        header['ConsistencyLevel'] = 'Eventual'
        header['Content-type'] = "application/json"


        url = f"https://graph.microsoft.com/v1.0/devices/{device_id}"
        #url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members/{quote_plus(user_email)}/$ref"
        response = requests.get(url, headers=header)
        return response.json()

    def get_all_devices(self, header=None):
        """ No paramaters needed"""
        header = self._set_header(header)
        # Required for this url
        header['ConsistencyLevel'] = 'Eventual'
        header['Content-type'] = "application/json"


        url = "https://graph.microsoft.com/v1.0/devices"
        response = requests.get(url, headers=header)
        return response.json()

    def get_user_devices(self, user, header=None):
        """ No paramaters needed"""

        header = self._set_header(header)
        # Required for this url
        header['ConsistencyLevel'] = 'Eventual'
        header['Content-type'] = "application/json"

        url = "https://graph.microsoft.com/v1.0/devices"
        response = requests.get(url, headers=header)
        return response.json()

    def mem_get_device(self, managedDeviceId, header=None):
        """ No paramaters needed"""

        header = self._set_header(header)
        # Required for this url
        header['ConsistencyLevel'] = 'Eventual'
        header['Content-type'] = "application/json"

        url = f"https://graph.microsoft.com/v1.0/deviceManagement/managedDevices/{managedDeviceId}"
        response = requests.get(url, headers=header)
        return response.json()

    def mem_get_all_devices(self, header=None):
        """ No paramaters needed"""

        header = self._set_header(header)
        # Required for this url
        header['ConsistencyLevel'] = 'Eventual'
        header['Content-type'] = "application/json"

        url = "https://graph.microsoft.com/v1.0//deviceManagement/managedDevices"
        response = requests.get(url, headers=header)
        return response.json()

    def host_pool_get_pool(self, subscription_id, host_pool_resource_group_name, host_pool_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param host_pool_name:
        :param header:
        :return:
        """
        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{host_pool_resource_group_name}/providers/Microsoft.DesktopVirtualization/hostPools/{host_pool_name}?api-version={self.__hostpool_api_version}"
        response = requests.get(url, headers=header)
        return response.json()

    def host_pool_list_all_pools(self, subscription_id, header=None):
        """
        :param subscription_id:
        :param header:
        :return:
        """
        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.DesktopVirtualization/hostPools?api-version={self.__hostpool_api_version}"
        all_host_pools = []
        response = requests.get(url, headers=header)
        while response:
            all_host_pools += response.json()['value']
            response = requests.get(response.json()['nextLink'], headers=header) if response.json()['nextLink'] else None

        return all_host_pools


    def host_pool_get_active_users(self, subscription_id, host_pool_resource_group_name, host_pool_name, filter=None, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param host_pool_name:
        :param filter: $filter=userPrincipalName eq 'user1@microsoft.com' and state eq 'active'
        :param header:
        :return:
        """
        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{host_pool_resource_group_name}/providers/Microsoft.DesktopVirtualization/hostPools/{host_pool_name}/userSessions?api-version={self.__hostpool_api_version}"
        if filter:
            url += f"&$filter={filter}"

        response = requests.get(url, headers=header)

        return response.json()

    def host_pool_get_all_virtual_machines(self, subscription_id, host_pool_resource_group_name, host_pool_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param host_pool_name:
        :param filter: $filter=userPrincipalName eq 'user1@microsoft.com' and state eq 'active'
        :param header:
        :return:
        """
        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{host_pool_resource_group_name}/providers/Microsoft.DesktopVirtualization/hostPools/{host_pool_name}/sessionHosts?api-version={self.__hostpool_api_version}"

        all_vms = []
        response = requests.get(url, headers=header)
        while response:
            all_vms += response.json()['value']
            response = requests.get(response.json()['nextLink'], headers=header) if response.json()['nextLink'] else None

        return all_vms


    def host_pool_assign_virtual_desktop(self, subscription_id, host_pool_resource_group_name, host_pool_name,
                                         host_pool_virtual_machine_name,user_email,
                                         friendly_name=None, allow_new_session=True, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param host_pool_name:
        :param filter: $filter=userPrincipalName eq 'user1@microsoft.com' and state eq 'active'
        :param header:
        :return:
        """
        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/" \
              f"resourceGroups/{host_pool_resource_group_name}/" \
              f"providers/Microsoft.DesktopVirtualization/" \
              f"hostPools/{host_pool_name}/" \
              f"sessionHosts/{host_pool_virtual_machine_name}" \
              f"?api-version={self.__hostpool_api_version}&force=True"

        payload = {
              "properties": {
                  "allowNewSession": allow_new_session,
                  "assignedUser": user_email,
              }
            }

        if friendly_name:
            payload["properties"]["friendlyName"] = friendly_name

        response = requests.patch(url, data=json.dumps(payload), headers=header)

        return response.json()

    def host_pool_unassign_virtual_desktop(self, subscription_id, host_pool_resource_group_name, host_pool_name,
                                         host_pool_virtual_machine_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param host_pool_name:
        :param filter: $filter=userPrincipalName eq 'user1@microsoft.com' and state eq 'active'
        :param header:
        :return:
        """
        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/" \
              f"resourceGroups/{host_pool_resource_group_name}/" \
              f"providers/Microsoft.DesktopVirtualization/" \
              f"hostPools/{host_pool_name}/" \
              f"sessionHosts/{host_pool_virtual_machine_name}" \
              f"?api-version={self.__hostpool_api_version}&force=True"

        payload = {
              "properties": {
                  "assignedUser": "",
                  "friendlyName": ""
              }
            }

        response = requests.patch(url, data=json.dumps(payload), headers=header)

        return response.json()

    def host_pool_delete_virtual_desktop(self, subscription_id, host_pool_resource_group_name, host_pool_name,
                                         session_host_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param host_pool_name:
        :param session_host_name: DELETE https://management.azure.com/subscriptions/
        daefabc0-95b4-48b3-b645-8a753a63c4fa/resourceGroups/resourceGroup1/providers/
        Microsoft.DesktopVirtualization/hostPools/hostPool1/sessionHosts/sessionHost1.microsoft.com
        ?api-version=2022-02-10-preview&force=True
        :param header:
        :return:
        """
        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/" \
              f"{host_pool_resource_group_name}/providers/Microsoft.DesktopVirtualization/hostPools/" \
              f"{host_pool_name}/sessionHosts/{session_host_name}?api-version={self.__hostpool_api_version}&force=True"


        response = requests.delete(url, headers=header)

        return response.json()

    def host_pool_get_registration_key(self, subscription_id, host_pool_resource_group_name, host_pool_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param host_pool_name:
        :param filter: $filter=userPrincipalName eq 'user1@microsoft.com' and state eq 'active'
        :param header:
        :return:
        """
        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/" \
              f"resourceGroups/{host_pool_resource_group_name}/" \
              f"providers/Microsoft.DesktopVirtualization/" \
              f"hostPools/{host_pool_name}/" \
              f"retrieveRegistrationToken?api-version={self.__hostpool_api_version}"
        response = requests.post(url, headers=header)

        return response.json()




    def virtual_machine_create(self, subscription_id, host_pool_resource_group_name,
                                         virtual_machine_name, settings_payload=None, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param virtual_machine_name:
        :param header:
        :return:
        https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/list?tabs=HTTP#code-try-0
        """

        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        if not settings_payload:
            return {"response": "500",
                    "message": "You need payload settings for your virtual machine "
                               "https://learn.microsoft.com/en-us/rest/api/compute/"
                               "virtual-machines/create-or-update?tabs=HTTP"}

        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/" \
              f"{host_pool_resource_group_name}/providers/Microsoft.Compute/virtualMachines/" \
              f"{virtual_machine_name}?api-version={self.__virtual_machine_api_version}"

        response = requests.put(url, data=json.dumps(settings_payload), headers=header)

        return response.json()

    def virtual_machine_restart(self, subscription_id, host_pool_resource_group_name,
                                         virtual_machine_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param virtual_machine_name:
        :param header:
        :return:
        https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/list?tabs=HTTP#code-try-0
        """

        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/" \
              f"{host_pool_resource_group_name}/providers/Microsoft.Compute/virtualMachines/" \
              f"{virtual_machine_name}/restart?api-version={self.__virtual_machine_api_version}"

        response = requests.post(url, headers=header)

        return response.json()

    def virtual_machine_reimage(self, subscription_id, host_pool_resource_group_name,
                                         virtual_machine_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param virtual_machine_name:
        :param header:
        :return:
        https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/list?tabs=HTTP#code-try-0
        """

        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/" \
              f"{host_pool_resource_group_name}/providers/Microsoft.Compute/virtualMachines/" \
              f"{virtual_machine_name}/reimage?api-version={self.__virtual_machine_api_version}"

        response = requests.post(url, headers=header)

        return response.json()

    def virtual_machine_redeploy(self, subscription_id, host_pool_resource_group_name,
                                         virtual_machine_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param virtual_machine_name:
        :param header:
        :return:
        https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/list?tabs=HTTP#code-try-0
        """

        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/" \
              f"{host_pool_resource_group_name}/providers/Microsoft.Compute/virtualMachines/" \
              f"{virtual_machine_name}/redeploy?api-version={self.__virtual_machine_api_version}"

        response = requests.post(url, headers=header)

        return response.json()

    def virtual_machine_reapply(self, subscription_id, host_pool_resource_group_name,
                                         virtual_machine_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param virtual_machine_name:
        :param header:
        :return:
        https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/list?tabs=HTTP#code-try-0
        """

        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/" \
              f"{host_pool_resource_group_name}/providers/Microsoft.Compute/virtualMachines/" \
              f"{virtual_machine_name}/reapply?api-version={self.__virtual_machine_api_version}"

        response = requests.post(url, headers=header)

        return response.json()

    def virtual_machine_shutdown(self, subscription_id, host_pool_resource_group_name,
                                         virtual_machine_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param virtual_machine_name:
        :param header:
        :return:
        https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/list?tabs=HTTP#code-try-0
        """

        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/" \
              f"{host_pool_resource_group_name}/providers/Microsoft.Compute/virtualMachines/" \
              f"{virtual_machine_name}/powerOff?api-version={self.__virtual_machine_api_version}"

        response = requests.post(url, headers=header)

        return response.json()

    def virtual_machine_start(self, subscription_id, host_pool_resource_group_name,
                                         virtual_machine_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param virtual_machine_name:
        :param header:
        :return:
        https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/list?tabs=HTTP#code-try-0
        """

        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/" \
              f"{host_pool_resource_group_name}/providers/Microsoft.Compute/virtualMachines/" \
              f"{virtual_machine_name}/start?api-version={self.__virtual_machine_api_version}"

        response = requests.post(url, headers=header)

        return response.json()


    def virtual_machine_create_new_user(self, subscription_id, host_pool_resource_group_name,
                                         virtual_machine_name, vm_location, user_name, user_password,
                                        header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param virtual_machine_name:
        :param header:
        :return:
        https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/list?tabs=HTTP#code-try-0
        """

        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        payload = {
            "location": f"{vm_location}",
            "properties": {
                "source": {
                    "script": f"$Pass = ConvertTo-SecureString '{user_password}' -AsPlainText -Force; "
                              f"New-LocalUser -Name '{user_name}' "
                              f"-Description '{user_name}' "
                              f"-AccountNeverExpires "
                              f"-Password $Pass; "
                              f"Add-LocalGroupMember -Group 'Administrators' -Member '{user_name}'"
                },
                "asyncExecution": False,
                "timeoutInSeconds": 3600
            }
        }

        url = f"https://management.azure.com/subscriptions/{subscription_id}/" \
              f"resourceGroups/{host_pool_resource_group_name}/" \
              f"providers/Microsoft.Compute/" \
              f"virtualMachines/{virtual_machine_name}/" \
              f"runCommands/user-create" \
              f"?api-version={self.__virtual_machine_api_version}"

        response = requests.put(url, data=json.dumps(payload), headers=header)

        return response.json()

    def virtual_machine_send_script(self, subscription_id, host_pool_resource_group_name,
                                         virtual_machine_name, vm_location, script_block,
                                        header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param virtual_machine_name:
        :param header:
        :return:
        https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/list?tabs=HTTP#code-try-0
        """

        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        payload = {
            "location": f"{vm_location}",
            "properties": {
                "source": {
                    "script": script_block
                },
                "asyncExecution": False,
                "timeoutInSeconds": 3600
            }
        }

        url = f"https://management.azure.com/subscriptions/{subscription_id}/" \
              f"resourceGroups/{host_pool_resource_group_name}/" \
              f"providers/Microsoft.Compute/" \
              f"virtualMachines/{virtual_machine_name}/" \
              f"runCommands/custom_script" \
              f"?api-version={self.__virtual_machine_api_version}"

        response = requests.put(url, data=json.dumps(payload), headers=header)

        return response.json()

    def virtual_machine_delete_virtual_desktop(self, subscription_id, host_pool_resource_group_name,
                                               virtual_machine_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param host_pool_name:
        :param session_host_name:
        :param header:
        :return:
        """
        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"


        url = f"DELETE https://management.azure.com/subscriptions/{subscription_id}/" \
              f"resourceGroups/{host_pool_resource_group_name}/" \
              f"providers/Microsoft.Compute/" \
              f"virtualMachines/{virtual_machine_name}" \
              f"?forceDeletion=true" \
              f"&api-version={self.__virtual_machine_api_version}"


        response = requests.delete(url, headers=header)

        return response.json()


    def virtual_machine_install_extension(self, subscription_id, host_pool_resource_group_name,
                                         virtual_machine_name, extension_name,
                                          settings_payload=None, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param virtual_machine_name:
        :param header:
        :return:
        https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/list?tabs=HTTP#code-try-0
        """

        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        if not settings_payload:
            return {"response": "500",
                    "message": "You need payload settings for your virtual machine "
                               "https://learn.microsoft.com/en-us/rest/api/compute/"
                               "virtual-machines/create-or-update?tabs=HTTP"}

        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/" \
              f"{host_pool_resource_group_name}/providers/Microsoft.Compute/" \
              f"virtualMachines/{virtual_machine_name}/" \
              f"extensions/{extension_name}" \
              f"?api-version={self.__virtual_machine_api_version}"

        response = requests.put(url, data=json.dumps(settings_payload), headers=header)

        return response.json()

    def virtual_network_list(self, subscription_id, host_pool_resource_group_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param header:
        :return:
        """

        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/" \
              f"resourceGroups/{host_pool_resource_group_name}/providers/Microsoft.Network/" \
              f"virtualNetworks?api-version={self.__virtual_network_api_version}"

        response = requests.get(url, headers=header)

        return response.json()

    def virtual_network_get_nic(self, subscription_id, host_pool_resource_group_name, nic_name, header=None):
        """
        :param subscription_id:
        :param host_pool_resource_group_name:
        :param header:
        :return:
        """

        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/" \
              f"resourceGroups/{host_pool_resource_group_name}/" \
              f"providers/Microsoft.Network/" \
              f"networkInterfaces/{nic_name}?api-version={self.__virtual_network_api_version}"

        response = requests.get(url, headers=header)

        return response.json()

    def virtual_network_create_nic(self, subscription_id, host_pool_resource_group_name, nic_name,
                                   settings_payload, header=None):
        header = self._set_header(header)
        # Required for this url
        header['Content-type'] = "application/json"

        url = f"https://management.azure.com/subscriptions/{subscription_id}/" \
              f"resourceGroups/{host_pool_resource_group_name}/providers/Microsoft.Network/" \
              f"networkInterfaces/{nic_name}?api-version={self.__virtual_network_api_version}"
        response = requests.put(url, data=json.dumps(settings_payload), headers=header)

        return response.json()

