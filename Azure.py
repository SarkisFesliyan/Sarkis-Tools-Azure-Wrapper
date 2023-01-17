import json
from urllib.parse import quote_plus
import requests
import msal


class Azure:

    def __init__(self, tenant_id, client_id, secret):
        self.__tenant_id = tenant_id
        self.__client_id = client_id
        self.__secret = secret
        self.__header = None
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

    def auth(self,
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

    def _set_header(self, header=None):
        if not header:
            header = self.__header
        else:
            if "Authorization" not in header:
                if self.__header:
                    if 'Authorization' in self.__header:
                        header['Authorization'] = self.__header['Authorization']
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
        """ Takes user email or ID"""

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
        """ Takes user email or ID"""

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

    def mem_set_device_category(self, header=None):
        """ No paramaters needed"""

        header = self._set_header(header)
        # Required for this url
        header['ConsistencyLevel'] = 'Eventual'
        header['Content-type'] = "application/json"

        url = "https://graph.microsoft.com/v1.0//deviceManagement/deviceManagementScripts/{deviceManagementScriptId}/deviceRunStates/{deviceManagementScriptDeviceStateId}/managedDevice/deviceCategory"
        response = requests.patch(url, data=,headers=header)
        return response.json()
