def authenticate(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client
