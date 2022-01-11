# Sarkis-Tools-Azure-Wrapper
I created the module to easily contact the Azure AD table and grab user and group data. It was always a pain trying to find the extra headers and right urls. This module will take the pain out for you.

# Requirements
pip install msal

pip install requests

Create an app in your azure tenant and give access to read the directory objects.

# Usage steps
1: Create the object and authenticate
```python
import Azure
AD = Azure(TenantID, Client, SecretValue)
AD.auth()
```
By default you get these user fields but feel free to change them. set this to None if you want default fields to be returned instead.
```python
AD.user_fields = '&$select=accountEnabled,ageGroup,assignedLicenses,assignedPlans,assignedPlans,' \
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
```


2: Ask for a user. exact_match to get exact matches, value=value. memberof=True will do a second call to grab the memberOf fields for that user. 
```python
user = AD.get_displayname('Sarkis Fesliyan')
```
OR
```python
user = AD.get_username_new('sfesliyan', exact_match=False, memberof=True)
```
3: Find a group. Choose exact match or all results
```python
group = AD.get_group('okta-linux-users', exact_match=True)
```
4: Get a custom url endpoint if its something you need to tailer to your own needs.
```python
custom_endpoint = AD.get_url('https://graph.microsoft.com/v1.0/users/{user_id}/memberOf?$count=true')
```
5: Get all users in your environment. Ask for disabled user if you want.
```python
all_users = AD.get_all_users(disabled_users=False)
```

6: Get all disabled users
```python
disabled_users = AD.get_all_disabled_users()
```
7: Get all groups in your environement
```python
all_groups = AD.get_all_groups()
```